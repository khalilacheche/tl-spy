from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import get_tracker, get_network

router = APIRouter()


@router.get("/heatmap")
async def heatmap() -> dict:
    """Return current probability distribution across all stops."""
    tracker = get_tracker()
    network = get_network()
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

    return {"type": "FeatureCollection", "features": features}


@router.get("/stops")
async def stops() -> dict:
    """Return all stops in the network."""
    network = get_network()
    return {
        "stops": [
            {
                "id": s.id,
                "name": s.name,
                "lat": s.lat,
                "lon": s.lon,
                "lines": s.lines,
            }
            for s in network.stops.values()
        ]
    }


@router.get("/sightings")
async def sightings() -> dict:
    """Return recent sightings."""
    tracker = get_tracker()
    return {
        "sightings": [
            {
                "stop_id": s.stop_id,
                "timestamp": s.timestamp,
                "direction": s.direction,
                "line": s.line,
            }
            for s in tracker.sightings[-50:]
        ]
    }


@router.post("/sightings")
async def add_sighting(stop_id: str, line: str | None = None, direction: str | None = None) -> dict:
    """Manually report a sighting (for testing or manual input)."""
    import time
    from app.model.markov import Sighting

    sighting = Sighting(
        stop_id=stop_id,
        timestamp=time.time(),
        direction=direction,
        line=line,
    )
    tracker = get_tracker()
    tracker.report_sighting(sighting)
    return {"status": "ok", "sighting": {"stop_id": stop_id, "line": line, "direction": direction}}


_ws_clients: set[WebSocket] = set()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """WebSocket for real-time heatmap updates."""
    await ws.accept()
    _ws_clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        _ws_clients.discard(ws)


def get_ws_clients() -> set[WebSocket]:
    return _ws_clients
