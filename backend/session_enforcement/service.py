"""Apply session-risk policy after a proxy event is recorded."""

from __future__ import annotations

from datetime import datetime

from backend.analysis.rules import Decision
from backend.session_risk import calculate_session_risk

from .messages import review_message
from .models import SessionEnforcement
from .policy import enforcement_level, level_decision, level_reason, stronger_decision


def enforce_session_risk(
    *,
    session_id: int,
    timestamp: datetime,
    current_decision: Decision,
) -> SessionEnforcement:
    summary = calculate_session_risk(session_id)
    if summary is None:
        return SessionEnforcement(
            level="allow",
            decision=current_decision,
            reason=None,
            message=None,
            session_closed=False,
            requires_confirmation=False,
            risk_summary=None,
        )

    level = "stop" if summary.should_stop else enforcement_level(summary.session_risk_score)
    candidate_decision = level_decision(level)
    if current_decision == Decision.ALLOW and candidate_decision == Decision.WARN:
        # Session risk warnings are not enforced yet; keep the current request decision.
        decision = current_decision
    else:
        decision = stronger_decision(current_decision, candidate_decision)
    reason = summary.stop_reason or level_reason(level, summary.session_risk_score)
    message = review_message(session_id, summary.session_risk_score) if level == "stop" else None

    return SessionEnforcement(
        level=level,
        decision=decision,
        reason=reason,
        message=message,
        session_closed=False,
        requires_confirmation=level == "confirm",
        risk_summary=summary.to_dict(),
    )
