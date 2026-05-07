from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum

from app.data.network import TransportNetwork


class SightingState(str, Enum):
    AT_STOP = "at_stop"
    IN_TRANSIT = "in_transit"
    BOARDED = "boarded"
    ALIGHTED = "alighted"
    WALKING = "walking"


@dataclass
class Sighting:
    stop_id: str
    timestamp: float
    direction: str | None = None
    line: str | None = None
    confidence: float = 1.0
    state: SightingState = SightingState.AT_STOP
    count: int = 1


class AgentState(str, Enum):
    RIDING = "riding"
    AT_STOP = "at_stop"
    WALKING = "walking"
    EXITED = "exited"


# Speeds in km/h
SPEED_METRO = 30.0
SPEED_BUS = 18.0
SPEED_WALK = 4.0

AGENTS_PER_SIGHTING = 50
AGENT_TTL_SIM = 2700.0      # 45 sim-minutes
DECAY_HALF_LIFE_SIM = 900.0 # 15 sim-minutes
MERGE_DISTANCE_KM = 2.0
MERGE_MAX_AGE_SIM = 1800.0  # 30 sim-minutes


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@dataclass
class ControllerGroup:
    id: int
    origin_stop: str
    created_sim_time: float
    last_sighting_sim_time: float
    agents: list[Agent] = field(default_factory=list)


@dataclass
class Agent:
    lat: float
    lon: float
    state: AgentState
    weight: float
    born_sim_time: float = 0.0

    # Segment interpolation
    from_lat: float = 0.0
    from_lon: float = 0.0
    to_lat: float = 0.0
    to_lon: float = 0.0
    segment_km: float = 0.0
    segment_progress: float = 0.0  # 0.0 → 1.0
    speed_kmh: float = SPEED_BUS

    # Route plan
    route_ahead: list[str] = field(default_factory=list)
    line: str | None = None
    current_stop: str = ""

    # Stop behavior
    stop_wait_sec: float = 0.0     # sim-seconds to wait at current stop
    waited_sec: float = 0.0


class ControllerTracker:
    def __init__(self, network: TransportNetwork) -> None:
        self.network = network
        self.groups: list[ControllerGroup] = []
        self._next_group_id: int = 0
        self.sightings: list[Sighting] = []
        self.speed_multiplier: float = 5.0
        self.sim_time: float = time.time()  # simulated clock starts at real time
        self._last_real_time: float = time.time()

    @property
    def agent_count(self) -> int:
        return sum(len(g.agents) for g in self.groups)

    def report_sighting(self, sighting: Sighting) -> None:
        self.sightings.append(sighting)
        group = self._find_or_create_group(sighting)
        self._spawn_agents(sighting, group)

    def _find_or_create_group(self, sighting: Sighting) -> ControllerGroup:
        stop_id = sighting.stop_id
        if stop_id in self.network.stops:
            slat, slon = self._stop_pos(stop_id)
            for group in self.groups:
                if not group.agents:
                    continue
                if group.origin_stop not in self.network.stops:
                    continue
                glat, glon = self._stop_pos(group.origin_stop)
                dist = _haversine_km(slat, slon, glat, glon)
                age = self.sim_time - group.last_sighting_sim_time
                if dist < MERGE_DISTANCE_KM and age < MERGE_MAX_AGE_SIM:
                    group.last_sighting_sim_time = self.sim_time
                    return group

        group = ControllerGroup(
            id=self._next_group_id,
            origin_stop=stop_id,
            created_sim_time=self.sim_time,
            last_sighting_sim_time=self.sim_time,
        )
        self._next_group_id += 1
        self.groups.append(group)
        return group

    def _stop_pos(self, stop_id: str) -> tuple[float, float]:
        s = self.network.stops[stop_id]
        return s.lat, s.lon

    def _line_speed(self, line: str | None) -> float:
        if not line:
            return SPEED_BUS
        if line in ("M1", "M2"):
            return SPEED_METRO
        if line == "LEB":
            return SPEED_METRO
        return SPEED_BUS

    def _spawn_agents(self, sighting: Sighting, group: ControllerGroup | None = None) -> None:
        stop_id = sighting.stop_id
        if stop_id not in self.network.stops:
            return

        lat, lon = self._stop_pos(stop_id)
        line = sighting.line
        direction = sighting.direction

        # Build routes with direction awareness to avoid center bias
        directed_routes: list[tuple[str, list[str]]] = []   # routes that match the stated direction
        undirected_routes: list[tuple[str, list[str]]] = []  # fallback routes (random direction)

        if line:
            if direction:
                route = self.network.get_route_ahead(line, stop_id, direction)
                if route:
                    directed_routes.append((line, route))
            # Also get a random-direction route as fallback
            route = self.network.get_route_ahead(line, stop_id, None, random_if_no_dir=True)
            if route:
                undirected_routes.append((line, route))

        if not directed_routes and not undirected_routes:
            for cand in self.network.lines_at_stop(stop_id):
                if direction:
                    route = self.network.get_route_ahead(cand, stop_id, direction)
                    if route:
                        directed_routes.append((cand, route))
                route = self.network.get_route_ahead(cand, stop_id, None, random_if_no_dir=True)
                if route:
                    undirected_routes.append((cand, route))

        for _ in range(AGENTS_PER_SIGHTING):
            w = sighting.count / AGENTS_PER_SIGHTING
            # 70% of agents follow the stated direction, 30% go random
            if directed_routes and random.random() < 0.7:
                routes = directed_routes
            else:
                routes = directed_routes + undirected_routes if directed_routes else undirected_routes
            agent = self._make_agent(stop_id, lat, lon, w, sighting.state, routes)
            if group is not None:
                group.agents.append(agent)
            else:
                if self.groups:
                    self.groups[-1].agents.append(agent)

    def _make_agent(self, stop_id: str, lat: float, lon: float, weight: float,
                    state: SightingState, routes: list[tuple[str, list[str]]]) -> Agent:

        if state in (SightingState.IN_TRANSIT, SightingState.BOARDED) and routes:
            chosen_line, route = random.choice(routes)
            exit_idx = self._pick_exit(route)
            agent_route = route[:exit_idx + 1]
            return Agent(
                lat=lat, lon=lon, state=AgentState.RIDING, weight=weight,
                born_sim_time=self.sim_time, route_ahead=agent_route,
                line=chosen_line, current_stop=stop_id,
                speed_kmh=self._line_speed(chosen_line),
                from_lat=lat, from_lon=lon,
                to_lat=lat, to_lon=lon,
            )

        if state == SightingState.ALIGHTED:
            r = random.random()
            if r < 0.5:
                return Agent(lat=lat, lon=lon, state=AgentState.AT_STOP, weight=weight,
                             born_sim_time=self.sim_time, current_stop=stop_id,
                             stop_wait_sec=random.uniform(30, 300))
            elif r < 0.8:
                return self._make_walk_agent(stop_id, lat, lon, weight)
            else:
                return Agent(lat=lat, lon=lon, state=AgentState.EXITED, weight=weight,
                             born_sim_time=self.sim_time, current_stop=stop_id)

        if state == SightingState.WALKING:
            return self._make_walk_agent(stop_id, lat, lon, weight)

        # AT_STOP
        r = random.random()
        if r < 0.35 and routes:
            chosen_line, route = random.choice(routes)
            exit_idx = self._pick_exit(route)
            delay = random.uniform(10, 120)
            return Agent(
                lat=lat, lon=lon, state=AgentState.AT_STOP, weight=weight,
                born_sim_time=self.sim_time, route_ahead=route[:exit_idx + 1],
                line=chosen_line, current_stop=stop_id,
                speed_kmh=self._line_speed(chosen_line),
                stop_wait_sec=delay,
            )
        else:
            return Agent(lat=lat, lon=lon, state=AgentState.AT_STOP, weight=weight,
                         born_sim_time=self.sim_time, current_stop=stop_id,
                         stop_wait_sec=random.uniform(60, 600))

    def _make_walk_agent(self, stop_id: str, lat: float, lon: float, weight: float) -> Agent:
        neighbors = self.network.neighbors(stop_id)
        if neighbors:
            target, _ = random.choice(neighbors)
            return Agent(
                lat=lat, lon=lon, state=AgentState.WALKING, weight=weight,
                born_sim_time=self.sim_time, route_ahead=[target],
                current_stop=stop_id, speed_kmh=SPEED_WALK,
                from_lat=lat, from_lon=lon, to_lat=lat, to_lon=lon,
            )
        return Agent(lat=lat, lon=lon, state=AgentState.AT_STOP, weight=weight,
                     born_sim_time=self.sim_time, current_stop=stop_id,
                     stop_wait_sec=60)

    def _pick_exit(self, route: list[str]) -> int:
        for i, sid in enumerate(route):
            hub = self.network.hub_scores.get(sid, 1)
            # Flatter probability: hubs are slightly more likely exit points
            # but not strongly enough to cause center accumulation
            p = 0.04 + (hub / 20.0) * 0.08
            if i == len(route) - 1:
                return i
            if random.random() < p:
                return i
        return len(route) - 1

    def _begin_segment(self, agent: Agent) -> None:
        """Start moving toward the next stop in route_ahead."""
        if not agent.route_ahead:
            return
        next_stop = agent.route_ahead[0]
        if next_stop not in self.network.stops:
            agent.route_ahead.pop(0)
            return

        nlat, nlon = self._stop_pos(next_stop)
        agent.from_lat = agent.lat
        agent.from_lon = agent.lon
        agent.to_lat = nlat
        agent.to_lon = nlon
        agent.segment_km = _haversine_km(agent.lat, agent.lon, nlat, nlon)
        agent.segment_progress = 0.0

    def tick(self, real_dt: float) -> None:
        """Advance simulation by real_dt real seconds."""
        sim_dt = real_dt * self.speed_multiplier
        self.sim_time += sim_dt

        active_groups: list[ControllerGroup] = []
        for group in self.groups:
            alive: list[Agent] = []
            for agent in group.agents:
                age = self.sim_time - agent.born_sim_time
                if age > AGENT_TTL_SIM or agent.state == AgentState.EXITED:
                    continue

                if agent.state == AgentState.RIDING:
                    self._tick_riding(agent, sim_dt)
                elif agent.state == AgentState.AT_STOP:
                    self._tick_at_stop(agent, sim_dt)
                elif agent.state == AgentState.WALKING:
                    self._tick_walking(agent, sim_dt)

                alive.append(agent)

            group.agents = alive
            if alive:
                active_groups.append(group)

        self.groups = active_groups

    def _tick_riding(self, agent: Agent, sim_dt: float) -> None:
        # If not on a segment yet, start one
        if agent.segment_km == 0 and agent.route_ahead:
            self._begin_segment(agent)

        if agent.segment_km > 0:
            # Advance along segment
            speed_km_s = agent.speed_kmh / 3600.0
            dist_traveled = speed_km_s * sim_dt
            agent.segment_progress += dist_traveled / agent.segment_km

            if agent.segment_progress >= 1.0:
                # Arrived at next stop
                next_stop = agent.route_ahead.pop(0)
                nlat, nlon = self._stop_pos(next_stop)
                agent.lat = nlat
                agent.lon = nlon
                agent.current_stop = next_stop
                agent.segment_km = 0
                agent.segment_progress = 0

                if agent.route_ahead:
                    # Keep riding — start next segment
                    self._begin_segment(agent)
                else:
                    # End of route — get off
                    agent.state = AgentState.AT_STOP
                    agent.waited_sec = 0
                    agent.stop_wait_sec = random.uniform(30, 180)
            else:
                # Interpolate position
                agent.lat = agent.from_lat + (agent.to_lat - agent.from_lat) * agent.segment_progress
                agent.lon = agent.from_lon + (agent.to_lon - agent.from_lon) * agent.segment_progress
        elif not agent.route_ahead:
            agent.state = AgentState.AT_STOP
            agent.waited_sec = 0
            agent.stop_wait_sec = random.uniform(30, 180)

    def _tick_at_stop(self, agent: Agent, sim_dt: float) -> None:
        agent.waited_sec += sim_dt

        if agent.waited_sec >= agent.stop_wait_sec:
            if agent.route_ahead:
                # Board planned route
                agent.state = AgentState.RIDING
                self._begin_segment(agent)
            else:
                r = random.random()
                if r < 0.10:
                    lines = self.network.lines_at_stop(agent.current_stop)
                    if lines:
                        line = random.choice(lines)
                        route = self.network.get_route_ahead(line, agent.current_stop, None, random_if_no_dir=True)
                        if route:
                            exit_idx = self._pick_exit(route)
                            agent.route_ahead = route[:exit_idx + 1]
                            agent.line = line
                            agent.speed_kmh = self._line_speed(line)
                            agent.state = AgentState.RIDING
                            self._begin_segment(agent)
                            return
                elif r < 0.25:
                    neighbors = self.network.neighbors(agent.current_stop)
                    if neighbors:
                        target, _ = random.choice(neighbors)
                        agent.route_ahead = [target]
                        agent.speed_kmh = SPEED_WALK
                        agent.state = AgentState.WALKING
                        self._begin_segment(agent)
                        return
                elif r < 0.40:
                    agent.state = AgentState.EXITED
                    return

                # Otherwise keep waiting
                agent.stop_wait_sec += random.uniform(30, 120)

    def _tick_walking(self, agent: Agent, sim_dt: float) -> None:
        if agent.segment_km == 0 and agent.route_ahead:
            self._begin_segment(agent)

        if agent.segment_km > 0:
            speed_km_s = SPEED_WALK / 3600.0
            dist = speed_km_s * sim_dt
            agent.segment_progress += dist / agent.segment_km

            if agent.segment_progress >= 1.0:
                next_stop = agent.route_ahead.pop(0)
                nlat, nlon = self._stop_pos(next_stop)
                agent.lat = nlat
                agent.lon = nlon
                agent.current_stop = next_stop
                agent.segment_km = 0
                agent.segment_progress = 0
                agent.state = AgentState.AT_STOP
                agent.waited_sec = 0
                agent.stop_wait_sec = random.uniform(30, 120)
            else:
                agent.lat = agent.from_lat + (agent.to_lat - agent.from_lat) * agent.segment_progress
                agent.lon = agent.from_lon + (agent.to_lon - agent.from_lon) * agent.segment_progress
        else:
            agent.state = AgentState.AT_STOP
            agent.waited_sec = 0
            agent.stop_wait_sec = 60

    def get_heatmap_points(self) -> list[tuple[float, float, float]]:
        """Return interpolated (lat, lon, weight) for all live agents across all groups."""
        points: list[tuple[float, float, float]] = []
        for group in self.groups:
            for agent in group.agents:
                if agent.state == AgentState.EXITED:
                    continue
                age = self.sim_time - agent.born_sim_time
                decay = math.exp(-age * 0.693 / DECAY_HALF_LIFE_SIM)
                w = agent.weight * decay
                if w > 1e-6:
                    points.append((agent.lat, agent.lon, w))
        return points

    def get_line_risks(self) -> list[dict]:
        """Return per-line risk scores sorted by risk descending."""
        line_weights: dict[str, float] = {}
        line_agents: dict[str, int] = {}
        for group in self.groups:
            for agent in group.agents:
                if agent.state == AgentState.EXITED:
                    continue
                age = self.sim_time - agent.born_sim_time
                decay = math.exp(-age * 0.693 / DECAY_HALF_LIFE_SIM)
                w = agent.weight * decay
                if w < 1e-6:
                    continue

                lines: set[str] = set()
                if agent.line:
                    lines.add(agent.line)
                if agent.current_stop:
                    for ln, route in self.network.line_routes.items():
                        if agent.current_stop in route:
                            lines.add(ln)

                for ln in lines:
                    line_weights[ln] = line_weights.get(ln, 0.0) + w
                    line_agents[ln] = line_agents.get(ln, 0) + 1

        if not line_weights:
            return []

        max_w = max(line_weights.values())
        results = []
        for ln, w in line_weights.items():
            results.append({
                "line": ln,
                "risk": round(w / max_w, 3),
                "agents": line_agents.get(ln, 0),
            })
        results.sort(key=lambda x: x["risk"], reverse=True)
        return results

    def get_heatmap(self) -> dict[str, float]:
        """Legacy stop-based heatmap for the REST endpoint."""
        counts: dict[str, float] = {}
        for group in self.groups:
            for agent in group.agents:
                if agent.state == AgentState.EXITED:
                    continue
                age = self.sim_time - agent.born_sim_time
                decay = math.exp(-age * 0.693 / DECAY_HALF_LIFE_SIM)
                sid = agent.current_stop or "unknown"
                counts[sid] = counts.get(sid, 0.0) + agent.weight * decay
        total = sum(counts.values())
        if total > 0:
            return {sid: v / total for sid, v in counts.items()}
        return {}
