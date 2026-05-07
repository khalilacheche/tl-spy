"""
Telegram channel scraper using Telethon.

Listens for new messages in the configured channel and attempts to extract
controller sighting info (location, line, direction).
"""

from __future__ import annotations

import logging
import re
import time

from telethon import TelegramClient, events

from app.config import settings
from app.data.network import TransportNetwork
from app.model.markov import ControllerTracker, Sighting

logger = logging.getLogger(__name__)

# Simple keyword → stop_id mapping (extend as needed)
KEYWORD_TO_STOP: dict[str, str] = {
    "flon": "m2_flon",
    "lausanne-flon": "m2_flon",
    "ouchy": "m2_ouchy",
    "grancy": "m2_grancy",
    "riponne": "m2_riponne",
    "bessières": "m2_bessieres",
    "bessieres": "m2_bessieres",
    "sallaz": "m2_sallaz",
    "vennes": "m2_vennes",
    "croisettes": "m2_croisettes",
    "gare": "m2_gare",
    "lausanne gare": "m2_gare",
    "renens": "m1_renens",
    "malley": "m1_malley",
    "bourdonnette": "m1_bourdonnette",
    "unil": "m1_unil_sorge",
    "sorge": "m1_unil_sorge",
    "mouline": "m1_unil_mouline",
    "chauderon": "b1_chauderon",
    "tunnel": "b1_tunnel",
    "pontaise": "b1_pontaise",
    "blécherette": "b1_blecherette",
    "blecherette": "b1_blecherette",
    "maladière": "b1_maladiere",
    "maladiere": "b1_maladiere",
    "prilly": "b2_prilly",
    "désert": "b2_desert",
    "desert": "b2_desert",
}

LINE_PATTERNS = [
    (re.compile(r"\bm1\b", re.IGNORECASE), "M1"),
    (re.compile(r"\bm2\b", re.IGNORECASE), "M2"),
    (re.compile(r"\bbus\s*1\b", re.IGNORECASE), "Bus 1"),
    (re.compile(r"\bbus\s*2\b", re.IGNORECASE), "Bus 2"),
]

DIRECTION_PATTERN = re.compile(
    r"(?:direction|vers|heading|going|→|->)\s+(\w+)", re.IGNORECASE
)


def parse_message(text: str) -> Sighting | None:
    """Try to extract a controller sighting from a message."""
    text_lower = text.lower()

    stop_id = None
    for keyword, sid in KEYWORD_TO_STOP.items():
        if keyword in text_lower:
            stop_id = sid
            break

    if stop_id is None:
        return None

    line = None
    for pattern, line_name in LINE_PATTERNS:
        if pattern.search(text):
            line = line_name
            break

    direction = None
    dir_match = DIRECTION_PATTERN.search(text)
    if dir_match:
        dir_keyword = dir_match.group(1).lower()
        direction = KEYWORD_TO_STOP.get(dir_keyword)

    return Sighting(
        stop_id=stop_id,
        timestamp=time.time(),
        direction=direction,
        line=line,
    )


class TelegramScraper:
    def __init__(self, tracker: ControllerTracker, network: TransportNetwork) -> None:
        self.tracker = tracker
        self.network = network
        self.client: TelegramClient | None = None

    async def start(self) -> None:
        self.client = TelegramClient(
            "tl_spy_session",
            settings.telegram_api_id,
            settings.telegram_api_hash,
        )
        await self.client.start()

        @self.client.on(events.NewMessage(chats=settings.telegram_channel))
        async def on_message(event: events.NewMessage.Event) -> None:
            if not event.message.text:
                return

            sighting = parse_message(event.message.text)
            if sighting:
                logger.info(f"Sighting detected: {sighting.stop_id} on {sighting.line}")
                self.tracker.report_sighting(sighting)

        logger.info(f"Listening to Telegram channel: {settings.telegram_channel}")

    async def stop(self) -> None:
        if self.client:
            await self.client.disconnect()
