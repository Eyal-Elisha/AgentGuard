"""Data shapes used by session risk scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventRiskPoint:
    event_id: int
    timestamp: str
    risk_score: float
    guard_action: str


@dataclass(frozen=True)
class SessionRiskInputs:
    events: list[EventRiskPoint]
    sensitive_interaction_count: int
    hard_block_count: int


@dataclass(frozen=True)
class SessionRiskSummary:
    session_risk_score: float
    risk_level: str
    should_stop: bool
    stop_reason: str | None
    highest_event_risk: float
    recent_weighted_risk: float
    risky_event_count: int
    warn_count: int
    block_count: int
    sensitive_interaction_count: int
    hard_block_count: int
    risk_trend: str
    average_risk_score: float

    def to_dict(self) -> dict:
        return {
            "session_risk_score": self.session_risk_score,
            "risk_level": self.risk_level,
            "should_stop": self.should_stop,
            "stop_reason": self.stop_reason,
            "highest_event_risk": self.highest_event_risk,
            "recent_weighted_risk": self.recent_weighted_risk,
            "risky_event_count": self.risky_event_count,
            "warn_count": self.warn_count,
            "block_count": self.block_count,
            "sensitive_interaction_count": self.sensitive_interaction_count,
            "hard_block_count": self.hard_block_count,
            "risk_trend": self.risk_trend,
            "average_risk_score": self.average_risk_score,
        }
