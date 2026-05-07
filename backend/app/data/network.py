from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Stop:
    id: str
    name: str
    lat: float
    lon: float
    lines: list[str] = field(default_factory=list)


class TransportNetwork:
    def __init__(self) -> None:
        self.stops: dict[str, Stop] = {}
        # Ordered stop sequences per line: {"M2": ["ouchy_olympique", "jordils", ..., "croisettes"]}
        self.line_routes: dict[str, list[str]] = {}
        # Adjacency: stop_id -> [(neighbor_id, line)]
        self._adjacency: dict[str, list[tuple[str, str]]] = {}
        # Hub scores: higher = more connections = more likely to exit/transfer
        self.hub_scores: dict[str, float] = {}

    def neighbors(self, stop_id: str) -> list[tuple[str, str]]:
        return self._adjacency.get(stop_id, [])

    def get_route_ahead(self, line: str, current_stop: str, direction_stop: str | None,
                        random_if_no_dir: bool = False) -> list[str] | None:
        """Get the ordered list of stops ahead on a line, given current position and direction."""
        route = self.line_routes.get(line)
        if not route:
            return None

        if current_stop not in route:
            return None

        idx = route.index(current_stop)
        forward = route[idx + 1:]
        backward = list(reversed(route[:idx]))

        if direction_stop and direction_stop in route:
            dir_idx = route.index(direction_stop)
            if dir_idx > idx:
                return forward
            else:
                return backward

        if random_if_no_dir:
            import random
            if forward and backward:
                return random.choice([forward, backward])
            return forward or backward

        # Default: return whichever side has stops
        return forward or backward

    def lines_at_stop(self, stop_id: str) -> list[str]:
        """Get all lines that pass through a stop."""
        lines = set()
        for line, route in self.line_routes.items():
            if stop_id in route:
                lines.add(line)
        return sorted(lines)


def _normalize_line_label(route_name: str) -> str:
    if route_name in ("m1", "m2"):
        return route_name.upper()
    elif route_name.startswith("N"):
        return f"Noctambus {route_name[1:]}"
    elif route_name == "R20":
        return "LEB"
    elif route_name.startswith("Bus-"):
        return route_name
    else:
        return f"Bus {route_name}"


def build_lausanne_network() -> TransportNetwork:
    net = TransportNetwork()

    gtfs_path = Path(__file__).parent / "gtfs_tl.json"
    with open(gtfs_path) as f:
        data = json.load(f)

    # Build GTFS ID → simplified ID mapping
    gtfs_to_simple: dict[str, str] = {}
    seen_simple: dict[str, str] = {}  # simple_id -> first gtfs_id

    for gtfs_id, info in data["stops"].items():
        raw_name = info["name"]
        # Keep city prefix to avoid collisions (e.g., "Lausanne, gare" vs "Sugnens, gare")
        # but strip it for the display name
        short_name = raw_name.split(", ", 1)[1] if ", " in raw_name else raw_name
        simple = raw_name.lower().replace(",", "").replace(" ", "_").replace("-", "_").replace(".", "").replace("'", "")

        gtfs_to_simple[gtfs_id] = simple

        if simple in seen_simple:
            # Merge lines into existing stop
            if simple in net.stops:
                for line in info["lines"]:
                    if line not in net.stops[simple].lines:
                        net.stops[simple].lines.append(line)
            continue

        seen_simple[simple] = gtfs_id
        net.stops[simple] = Stop(
            id=simple,
            name=short_name,
            lat=info["lat"],
            lon=info["lon"],
            lines=list(info["lines"]),
        )

    # Build line routes (ordered stop sequences) and adjacency
    for route_name, gtfs_stop_ids in data["routes"].items():
        line_label = _normalize_line_label(route_name)

        # Convert GTFS IDs to simplified IDs, dedup consecutive
        simple_stops: list[str] = []
        for gid in gtfs_stop_ids:
            sid = gtfs_to_simple.get(gid)
            if sid and sid in net.stops:
                if not simple_stops or simple_stops[-1] != sid:
                    simple_stops.append(sid)

        if len(simple_stops) < 2:
            continue

        net.line_routes[line_label] = simple_stops

        # Build adjacency from consecutive stops
        for i in range(len(simple_stops) - 1):
            a, b = simple_stops[i], simple_stops[i + 1]
            net._adjacency.setdefault(a, []).append((b, line_label))
            net._adjacency.setdefault(b, []).append((a, line_label))

    # Compute hub scores: number of unique lines through each stop
    for stop_id in net.stops:
        lines = set()
        for neighbor_id, line in net.neighbors(stop_id):
            lines.add(line)
        net.hub_scores[stop_id] = len(lines)

    return net
