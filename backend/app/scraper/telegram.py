"""
Telegram Bot API scraper using httpx long-polling.
Messages are parsed by Claude via the parser module.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.config import settings
from app.data.network import TransportNetwork
from app.model.markov import ControllerTracker
from app.scraper.parser import parse_message

logger = logging.getLogger(__name__)

BOT_API = "https://api.telegram.org/bot{token}"


class TelegramBotScraper:
    def __init__(self, tracker: ControllerTracker, network: TransportNetwork) -> None:
        self.tracker = tracker
        self.network = network
        self.base_url = BOT_API.format(token=settings.telegram_bot_token)
        self._offset = 0
        self._task: asyncio.Task | None = None  # type: ignore[type-arg]
        self._running = False

    async def start(self) -> None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/getMe")
            data = resp.json()
            if not data.get("ok"):
                raise RuntimeError(f"Bot token invalid: {data}")
            bot_name = data["result"]["username"]
            logger.info(f"Bot authenticated as @{bot_name}")

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Telegram bot polling started")

    async def _poll_loop(self) -> None:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            while self._running:
                try:
                    resp = await client.get(
                        f"{self.base_url}/getUpdates",
                        params={"offset": self._offset, "timeout": 30},
                    )
                    data = resp.json()

                    if not data.get("ok"):
                        logger.error(f"getUpdates error: {data}")
                        await asyncio.sleep(5)
                        continue

                    for update in data.get("result", []):
                        self._offset = update["update_id"] + 1
                        msg = update.get("message") or update.get("channel_post")
                        if not msg or not msg.get("text"):
                            continue

                        chat_title = msg["chat"].get("title", "")
                        text = msg["text"]

                        logger.debug(f"[{chat_title}] {text[:80]}")

                        sighting = await parse_message(text, self.network)
                        if sighting:
                            logger.info(
                                f"Sighting: {sighting.stop_id}"
                                f"{f' on {sighting.line}' if sighting.line else ''}"
                                f"{f' → {sighting.direction}' if sighting.direction else ''}"
                            )
                            self.tracker.report_sighting(sighting)

                except httpx.TimeoutException:
                    continue
                except Exception:
                    logger.exception("Polling error")
                    await asyncio.sleep(5)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
