"""User-facing messages for session enforcement."""

from __future__ import annotations


def review_message(session_id: int, score: float) -> str:
    return (
        f"Session #{session_id} reached risk score {score:.2f}. "
        "You should probably check yourself because this session is behaving unsafely."
    )


def no_active_session_message() -> str:
    return (
        "AgentGuard blocked this request because there is no active proxy session. "
        "Start a new session before continuing."
    )
