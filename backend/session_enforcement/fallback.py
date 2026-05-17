"""Fallback decision when the proxy has no open session."""

from __future__ import annotations

from backend.analysis.rules import Decision

from .messages import no_active_session_message
from .models import SessionEnforcement


def no_active_session_enforcement() -> SessionEnforcement:
    message = no_active_session_message()
    return SessionEnforcement(
        level="closed",
        decision=Decision.BLOCK,
        reason=message,
        message=message,
        session_closed=True,
        requires_confirmation=False,
        risk_summary=None,
    )
