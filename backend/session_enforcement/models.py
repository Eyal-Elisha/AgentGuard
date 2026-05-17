"""Data shapes for session-level enforcement."""

from __future__ import annotations

from dataclasses import dataclass

from backend.analysis.rules import Decision


@dataclass(frozen=True)
class SessionEnforcement:
    level: str
    decision: Decision
    reason: str | None
    message: str | None
    session_closed: bool
    requires_confirmation: bool
    risk_summary: dict | None

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "decision": self.decision.value,
            "reason": self.reason,
            "message": self.message,
            "session_closed": self.session_closed,
            "requires_confirmation": self.requires_confirmation,
            "risk_summary": self.risk_summary,
        }
