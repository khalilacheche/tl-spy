"""
Markov chain model for predicting controller positions.

Given a sighting at stop X at time T, propagate the probability distribution
forward in time using the transport network's transition matrix.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from app.data.network import TransportNetwork


@dataclass
class Sighting:
    stop_id: str
    timestamp: float  # unix epoch
    direction: str | None = None  # optional: heading towards stop Y
    line: str | None = None  # optional: which line they're on
    confidence: float = 1.0


class ControllerTracker:
    def __init__(self, network: TransportNetwork, step_interval_sec: float = 120.0) -> None:
        self.network = network
        self.step_interval = step_interval_sec
        self.transition_matrix = network.build_transition_matrix()
        self.stop_ids = network.stop_ids()
        self._idx = {sid: i for i, sid in enumerate(self.stop_ids)}
        self.sightings: list[Sighting] = []

    def report_sighting(self, sighting: Sighting) -> None:
        self.sightings.append(sighting)

    def _initial_distribution(self, sighting: Sighting) -> np.ndarray:
        """Create a probability distribution from a single sighting."""
        n = len(self.stop_ids)
        dist = np.zeros(n)

        if sighting.stop_id in self._idx:
            main_idx = self._idx[sighting.stop_id]
            dist[main_idx] = sighting.confidence

            if sighting.direction and sighting.direction in self._idx:
                dir_idx = self._idx[sighting.direction]
                dist[dir_idx] = sighting.confidence * 0.3
                dist[main_idx] = sighting.confidence * 0.7

        total = dist.sum()
        if total > 0:
            dist /= total

        return dist

    def get_heatmap(self, now: float | None = None) -> dict[str, float]:
        """Compute current probability heatmap across all stops by combining
        all sightings, each propagated forward from its report time to now."""
        if now is None:
            now = time.time()

        n = len(self.stop_ids)
        combined = np.zeros(n)

        if not self.sightings:
            return {sid: 0.0 for sid in self.stop_ids}

        for sighting in self.sightings:
            age_sec = now - sighting.timestamp
            if age_sec < 0:
                continue

            dist = self._initial_distribution(sighting)
            steps = int(age_sec / self.step_interval)

            # Cap steps — after ~30 steps the distribution is basically uniform
            steps = min(steps, 30)

            for _ in range(steps):
                dist = dist @ self.transition_matrix

            # Decay old sightings — less reliable over time
            decay = np.exp(-age_sec / 1800.0)  # 30-min half-life
            combined += dist * decay

        total = combined.sum()
        if total > 0:
            combined /= total

        return {self.stop_ids[i]: float(combined[i]) for i in range(n)}
