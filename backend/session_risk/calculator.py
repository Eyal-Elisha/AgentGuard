"""Calculate a session-level risk summary from persisted events."""

from __future__ import annotations

from backend.storage import sqlite_store as store

from .constants import (
    MAX_RISKY_EVENTS,
    MAX_SENSITIVE_INTERACTIONS,
    MAX_WARN_BLOCK_POINTS,
    RISK_WEIGHTS,
    RISKY_EVENT_THRESHOLD,
)
from .metrics import average_risk, clamp01, recent_weighted_risk, risk_trend
from .models import SessionRiskSummary
from .policy import risk_level, stop_reason
from .queries import load_session_risk_inputs


def _count_actions(events, action: str) -> int:
    return sum(1 for event in events if event.guard_action == action)


def calculate_session_risk(session_id: int) -> SessionRiskSummary | None:
    if store.session_get(session_id) is None:
        return None

    inputs = load_session_risk_inputs(session_id)
    events = inputs.events
    highest_risk = max((event.risk_score for event in events), default=0.0)
    recent_risk = recent_weighted_risk(events)
    risky_count = sum(
        1 for event in events if event.risk_score >= RISKY_EVENT_THRESHOLD
    )
    warn_count = _count_actions(events, "Warn")
    block_count = _count_actions(events, "Block")

    risky_score = clamp01(risky_count / MAX_RISKY_EVENTS)
    warn_block_score = clamp01(
        (warn_count + block_count * 2) / MAX_WARN_BLOCK_POINTS
    )
    sensitive_score = clamp01(
        inputs.sensitive_interaction_count / MAX_SENSITIVE_INTERACTIONS
    )

    score = (
        RISK_WEIGHTS["highest_event"] * highest_risk
        + RISK_WEIGHTS["recent_weighted"] * recent_risk
        + RISK_WEIGHTS["risky_event_count"] * risky_score
        + RISK_WEIGHTS["warn_block"] * warn_block_score
        + RISK_WEIGHTS["sensitive_interaction"] * sensitive_score
    )
    rounded_score = round(clamp01(score), 4)
    reason = stop_reason(
        score=rounded_score,
        block_count=block_count,
        hard_block_count=inputs.hard_block_count,
        sensitive_count=inputs.sensitive_interaction_count,
        recent_weighted_risk=recent_risk,
    )

    return SessionRiskSummary(
        session_risk_score=rounded_score,
        risk_level=risk_level(rounded_score),
        should_stop=reason is not None,
        stop_reason=reason,
        highest_event_risk=round(highest_risk, 4),
        recent_weighted_risk=round(recent_risk, 4),
        risky_event_count=risky_count,
        warn_count=warn_count,
        block_count=block_count,
        sensitive_interaction_count=inputs.sensitive_interaction_count,
        hard_block_count=inputs.hard_block_count,
        risk_trend=risk_trend(events),
        average_risk_score=round(average_risk(events), 4),
    )
