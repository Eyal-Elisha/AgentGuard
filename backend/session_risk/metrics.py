"""Small metric helpers for session risk scoring."""

from __future__ import annotations

from .constants import RECENT_EVENT_LIMIT, TREND_DELTA
from .models import EventRiskPoint


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def average_risk(events: list[EventRiskPoint]) -> float:
    if not events:
        return 0.0
    return sum(event.risk_score for event in events) / len(events)


def recent_weighted_risk(events: list[EventRiskPoint]) -> float:
    recent = events[-RECENT_EVENT_LIMIT:]
    if not recent:
        return 0.0

    weights = list(range(1, len(recent) + 1))
    weighted_sum = sum(
        event.risk_score * weight
        for event, weight in zip(recent, weights, strict=True)
    )
    return weighted_sum / sum(weights)


def risk_trend(events: list[EventRiskPoint]) -> str:
    if len(events) < 4:
        return "stable"

    recent = events[-RECENT_EVENT_LIMIT:]
    previous = events[: -len(recent)]
    if not previous:
        midpoint = len(events) // 2
        previous = events[:midpoint]
        recent = events[midpoint:]

    delta = average_risk(recent) - average_risk(previous)
    if delta >= TREND_DELTA:
        return "increasing"
    if delta <= -TREND_DELTA:
        return "decreasing"
    return "stable"
