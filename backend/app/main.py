from __future__ import annotations

import asyncio
import json
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_network, get_tracker
from app.api.routes import router, get_ws_clients
from app.config import settings
from app.scraper.telegram import TelegramScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scraper: TelegramScraper | None = None


async def broadcast_heatmap() -> None:
    """Periodically push heatmap updates to all WebSocket clients."""
    tracker = get_tracker()
    network = get_network()
    while True:
        await asyncio.sleep(10)
        clients = get_ws_clients()
        if not clients:
            continue

        probs = tracker.get_heatmap()
        features = []
        for stop_id, probability in probs.items():
            if stop_id not in network.stops:
                continue
            stop = network.stops[stop_id]
            features.append({
                "type": "Feature",
                "properties": {
                    "id": stop.id,
                    "name": stop.name,
                    "probability": probability,
                    "lines": stop.lines,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [stop.lon, stop.lat],
                },
            })

        payload = json.dumps({"type": "FeatureCollection", "features": features})

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

    if settings.telegram_api_id and settings.telegram_channel:
        scraper = TelegramScraper(tracker, network)
        try:
            await scraper.start()
        except Exception as e:
            logger.warning(f"Telegram scraper failed to start: {e}")
            logger.info("Running without live Telegram data — use POST /api/sightings to test")
    else:
        logger.info("No Telegram credentials configured — use POST /api/sightings to test")

    broadcast_task = asyncio.create_task(broadcast_heatmap())

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
