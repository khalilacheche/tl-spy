from __future__ import annotations

import asyncio
import json
import logging
import time

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_network, get_tracker
from app.api.routes import router, get_ws_clients
from app.config import settings
from app.scraper.telegram import TelegramBotScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scraper: TelegramBotScraper | None = None

TICK_INTERVAL = 0.3  # real seconds between ticks


async def simulation_loop() -> None:
    tracker = get_tracker()
    last_time = time.time()

    while True:
        await asyncio.sleep(TICK_INTERVAL)
        now = time.time()
        real_dt = now - last_time
        last_time = now

        tracker.tick(real_dt)

        clients = get_ws_clients()
        if not clients:
            continue

        points = tracker.get_heatmap_points()
        line_risks = tracker.get_line_risks()
        payload = json.dumps({
            "points": [[lat, lon, w] for lat, lon, w in points],
            "sim_time": tracker.sim_time,
            "speed": tracker.speed_multiplier,
            "agents": tracker.agent_count,
            "groups": len(tracker.groups),
            "line_risks": line_risks,
        })

        dead = set()
        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        clients -= dead


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scraper
    network = get_network()
    tracker = get_tracker()

    if settings.telegram_bot_token:
        scraper = TelegramBotScraper(tracker, network)
        try:
            await scraper.start()
        except Exception as e:
            logger.warning(f"Telegram bot failed to start: {e}")
            logger.info("Running without live Telegram data — use POST /api/sightings to test")
    else:
        logger.info("No TELEGRAM_BOT_TOKEN configured — use POST /api/sightings to test")

    broadcast_task = asyncio.create_task(simulation_loop())

    yield

    broadcast_task.cancel()
    if scraper:
        await scraper.stop()


app = FastAPI(title="TL Spy", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
