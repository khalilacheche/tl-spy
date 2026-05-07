"""
Lausanne TL transport network as a graph.

Nodes = stops, edges = direct connections on a line.
Weights on edges represent typical travel time in minutes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Stop:
    id: str
    name: str
    lat: float
    lon: float
    lines: list[str] = field(default_factory=list)


@dataclass
class Edge:
    from_stop: str
    to_stop: str
    line: str
    travel_time_min: float


class TransportNetwork:
    def __init__(self) -> None:
        self.stops: dict[str, Stop] = {}
        self.edges: list[Edge] = []
        self._adjacency: dict[str, list[tuple[str, str, float]]] = {}

    def add_stop(self, stop: Stop) -> None:
        self.stops[stop.id] = stop

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)
        self._adjacency.setdefault(edge.from_stop, []).append(
            (edge.to_stop, edge.line, edge.travel_time_min)
        )
        self._adjacency.setdefault(edge.to_stop, []).append(
            (edge.from_stop, edge.line, edge.travel_time_min)
        )

    def neighbors(self, stop_id: str) -> list[tuple[str, str, float]]:
        return self._adjacency.get(stop_id, [])

    def stop_ids(self) -> list[str]:
        return sorted(self.stops.keys())

    def build_transition_matrix(self, decay_minutes: float = 5.0) -> np.ndarray:
        """Build a Markov transition matrix where probability of moving to a
        neighbor is inversely proportional to travel time, with exponential decay."""
        ids = self.stop_ids()
        idx = {sid: i for i, sid in enumerate(ids)}
        n = len(ids)
        matrix = np.zeros((n, n))

        for sid in ids:
            i = idx[sid]
            for neighbor_id, _line, travel_time in self.neighbors(sid):
                j = idx[neighbor_id]
                matrix[i][j] += np.exp(-travel_time / decay_minutes)

        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        matrix /= row_sums

        return matrix


def build_lausanne_network() -> TransportNetwork:
    """Build a simplified Lausanne TL network with the major metro and bus lines."""
    net = TransportNetwork()

    # --- M1 Metro (Renens-Gare ↔ Lausanne-Flon) ---
    m1_stops = [
        ("m1_renens", "Renens-Gare", 46.5370, 6.5780),
        ("m1_epenex", "Epenex", 46.5390, 6.5830),
        ("m1_crochy", "Crochy", 46.5400, 6.5880),
        ("m1_cerisaie", "Cerisaie", 46.5410, 6.5920),
        ("m1_bassenges", "Bassenges", 46.5420, 6.5960),
        ("m1_unil_mouline", "UNIL-Mouline", 46.5380, 6.5990),
        ("m1_unil_sorge", "UNIL-Sorge", 46.5360, 6.6020),
        ("m1_bourdonnette", "Bourdonnette", 46.5340, 6.6060),
        ("m1_malley", "Malley", 46.5320, 6.6100),
        ("m1_flon", "Lausanne-Flon", 46.5197, 6.6298),
    ]
    for sid, name, lat, lon in m1_stops:
        net.add_stop(Stop(id=sid, name=name, lat=lat, lon=lon, lines=["M1"]))
    for i in range(len(m1_stops) - 1):
        net.add_edge(Edge(m1_stops[i][0], m1_stops[i + 1][0], "M1", 2.0))

    # --- M2 Metro (Ouchy ↔ Croisettes) ---
    m2_stops = [
        ("m2_ouchy", "Ouchy-Olympique", 46.5080, 6.6290),
        ("m2_jordils", "Jordils", 46.5100, 6.6300),
        ("m2_delegation", "Délégation", 46.5120, 6.6295),
        ("m2_grancy", "Grancy", 46.5150, 6.6310),
        ("m2_flon", "Lausanne-Flon", 46.5197, 6.6298),
        ("m2_riponne", "Riponne-M.Béjart", 46.5230, 6.6330),
        ("m2_bessieres", "Bessières", 46.5250, 6.6350),
        ("m2_ours", "Ours", 46.5260, 6.6340),
        ("m2_gare", "Lausanne-Gare CFF", 46.5165, 6.6294),
        ("m2_sallaz", "Sallaz", 46.5310, 6.6430),
        ("m2_vennes", "Vennes", 46.5350, 6.6530),
        ("m2_croisettes", "Croisettes", 46.5380, 6.6600),
    ]
    for sid, name, lat, lon in m2_stops:
        net.add_stop(Stop(id=sid, name=name, lat=lat, lon=lon, lines=["M2"]))
    for i in range(len(m2_stops) - 1):
        net.add_edge(Edge(m2_stops[i][0], m2_stops[i + 1][0], "M2", 1.5))

    # --- Bus 1 (simplified: Blécherette → Maladière) ---
    bus1_stops = [
        ("b1_blecherette", "Blécherette", 46.5380, 6.6220),
        ("b1_pontaise", "Pontaise", 46.5340, 6.6260),
        ("b1_tunnel", "Tunnel", 46.5280, 6.6310),
        ("b1_chauderon", "Chauderon", 46.5210, 6.6260),
        ("b1_maladiere", "Maladière", 46.5170, 6.6180),
    ]
    for sid, name, lat, lon in bus1_stops:
        net.add_stop(Stop(id=sid, name=name, lat=lat, lon=lon, lines=["Bus 1"]))
    for i in range(len(bus1_stops) - 1):
        net.add_edge(Edge(bus1_stops[i][0], bus1_stops[i + 1][0], "Bus 1", 3.0))

    # --- Bus 2 (simplified: Désert → Prilly) ---
    bus2_stops = [
        ("b2_desert", "Désert", 46.5300, 6.6500),
        ("b2_sallaz", "Sallaz", 46.5310, 6.6430),
        ("b2_chauderon", "Chauderon", 46.5210, 6.6260),
        ("b2_prilly", "Prilly-Centre", 46.5250, 6.5950),
    ]
    for sid, name, lat, lon in bus2_stops:
        if sid not in net.stops:
            net.add_stop(Stop(id=sid, name=name, lat=lat, lon=lon, lines=["Bus 2"]))
        else:
            net.stops[sid].lines.append("Bus 2")
    for i in range(len(bus2_stops) - 1):
        net.add_edge(Edge(bus2_stops[i][0], bus2_stops[i + 1][0], "Bus 2", 3.5))

    # Connect M1 and M2 at Flon (transfer edge)
    net.add_edge(Edge("m1_flon", "m2_flon", "transfer", 2.0))

    return net
