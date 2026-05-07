"""Singleton dependencies shared across the app."""

from __future__ import annotations

from app.data.network import TransportNetwork, build_lausanne_network
from app.model.markov import ControllerTracker

_network: TransportNetwork | None = None
_tracker: ControllerTracker | None = None


def get_network() -> TransportNetwork:
    global _network
    if _network is None:
        _network = build_lausanne_network()
    return _network


def get_tracker() -> ControllerTracker:
    global _tracker
    if _tracker is None:
        _tracker = ControllerTracker(get_network())
    return _tracker
