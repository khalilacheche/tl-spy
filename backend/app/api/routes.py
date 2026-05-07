from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import get_tracker, get_network

router = APIRouter()


@router.get("/heatmap")
async def heatmap() -> dict:
    tracker = get_tracker()
    network = get_network()
    probs = tracker.get_heatmap()

    features = []
    for stop_id, probability in probs.items():
        if stop_id not in network.stops or probability < 1e-6:
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
async def add_sighting(stop_id: str, line: str | None = None, direction: str | None = None,
                       state: str = "at_stop", count: int = 1) -> dict:
    import time
    from app.model.markov import Sighting, SightingState

    state_map = {s.value: s for s in SightingState}
    sighting = Sighting(
        stop_id=stop_id,
        timestamp=time.time(),
        direction=direction,
        line=line,
        state=state_map.get(state, SightingState.AT_STOP),
        count=max(1, min(count, 10)),
    )
    tracker = get_tracker()
    tracker.report_sighting(sighting)
    return {"status": "ok", "sighting": {"stop_id": stop_id, "line": line, "direction": direction}}


@router.get("/line-risks")
async def line_risks() -> dict:
    tracker = get_tracker()
    return {"lines": tracker.get_line_risks()}


@router.post("/speed")
async def set_speed(multiplier: float) -> dict:
    tracker = get_tracker()
    tracker.speed_multiplier = max(0.5, min(multiplier, 500.0))
    return {"speed": tracker.speed_multiplier}


@router.get("/speed")
async def get_speed() -> dict:
    tracker = get_tracker()
    return {"speed": tracker.speed_multiplier}


LINE_COLORS: dict[str, str] = {
    "M1": "#1e88e5",
    "M2": "#e53935",
    "LEB": "#43a047",
}


@router.get("/lines")
async def lines() -> dict:
    """Return polyline coordinates for each transit line."""
    network = get_network()
    result = []
    for line_name, stop_ids in network.line_routes.items():
        coords = []
        for sid in stop_ids:
            if sid in network.stops:
                s = network.stops[sid]
                coords.append([s.lat, s.lon])
        if len(coords) < 2:
            continue

        color = LINE_COLORS.get(line_name, "#666666")
        is_metro = line_name in ("M1", "M2")
        result.append({
            "name": line_name,
            "color": color,
            "weight": 4 if is_metro else 2,
            "opacity": 0.8 if is_metro else 0.4,
            "coords": coords,
        })
    return {"lines": result}


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
