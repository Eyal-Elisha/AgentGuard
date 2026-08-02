"""The lifetime of a proxy session.

A session spans one run of the proxy for one agent in one environment. Events
hang off it, and the contextual rules read their history from it, so exactly
one session must be open per (agent, environment) pair at a time — starting a
new one closes whatever it supersedes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.storage import sqlite_store as store

from .agents import DEFAULT_AGENT_NAME, normalize_proxy_agent_name
from .journal import iso_z, log_record

DEFAULT_ENVIRONMENT = "prod"


def resolve_proxy_session_id(
    *,
    session_id: int | None,
    timestamp: datetime,
    environment: str,
    agent_name: str,
) -> int:
    """The session id an inbound decision belongs to.

    Routes call this *before* evaluation so the evaluator can load prior-event
    context for the contextual rules, then reuse the same id when persisting.

    Raises ValueError when an explicit `session_id` does not exist, is already
    closed, or belongs to a different agent or environment — and when no
    session is open at all, since an event has nowhere to go without one.
    """
    _ensure_storage_ready()

    if session_id is None:
        open_session = store.session_get_latest_open_by_agent(agent_name, environment)
        if open_session is None:
            raise ValueError("No active proxy session is available")
        return int(open_session["session_id"])

    session = store.session_get(session_id)
    if session is None:
        raise ValueError("Provided session_id does not reference an existing session")
    if session.get("end_time") is not None:
        raise ValueError("Provided session_id is already closed")
    if str(session["environment"]) != environment:
        raise ValueError("Provided environment does not match the referenced session")
    if str(session["agent_name"]) != agent_name:
        raise ValueError("Provided agent_name does not match the referenced session")
    return int(session["session_id"])


def ensure_proxy_session_started(
    *,
    timestamp: datetime | None = None,
    environment: str = DEFAULT_ENVIRONMENT,
    agent_name: str = DEFAULT_AGENT_NAME,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Open a session, closing any session it supersedes for the same agent."""
    _ensure_storage_ready()

    started_at = timestamp or datetime.now(timezone.utc)
    agent = normalize_proxy_agent_name(agent_name)

    replaced_session_id = _close_superseded(agent, environment, started_at)

    session_id = store.session_create(
        user_id=user_id,
        start_time=started_at,
        environment=environment,
        agent_name=agent,
    )
    _log_session_event(
        "proxy_session_started",
        timestamp=started_at,
        agent=agent,
        environment=environment,
        session_id=session_id,
        replaced_session_id=replaced_session_id,
    )

    started = {
        "session_id": session_id,
        "agent": agent,
        "environment": environment,
        "created": True,
    }
    if replaced_session_id is not None:
        started["replaced_session_id"] = replaced_session_id
    return started


def close_proxy_session(
    *,
    timestamp: datetime | None = None,
    environment: str = DEFAULT_ENVIRONMENT,
    agent_name: str = DEFAULT_AGENT_NAME,
    reason: str = "proxy_stopped",
) -> dict[str, Any]:
    """Close the open session for this agent, if there is one."""
    _ensure_storage_ready()

    ended_at = timestamp or datetime.now(timezone.utc)
    agent = normalize_proxy_agent_name(agent_name)
    open_session = store.session_get_latest_open_by_agent(agent, environment)
    if open_session is None:
        return {"closed": False, "agent": agent, "environment": environment}

    session_id = int(open_session["session_id"])
    if store.session_try_close(session_id, ended_at) != "closed":
        return {
            "closed": False,
            "agent": agent,
            "environment": environment,
            "session_id": session_id,
        }

    _log_session_event(
        "proxy_session_closed",
        timestamp=ended_at,
        agent=agent,
        environment=environment,
        session_id=session_id,
        reason=reason,
    )
    return {
        "closed": True,
        "agent": agent,
        "environment": environment,
        "session_id": session_id,
    }


def _close_superseded(agent: str, environment: str, started_at: datetime) -> int | None:
    open_session = store.session_get_latest_open_by_agent(agent, environment)
    if open_session is None:
        return None

    session_id = int(open_session["session_id"])
    store.session_try_close(session_id, started_at)
    _log_session_event(
        "proxy_session_closed",
        timestamp=started_at,
        agent=agent,
        environment=environment,
        session_id=session_id,
        reason="superseded_by_new_proxy_session",
    )
    return session_id


def _log_session_event(
    event: str,
    *,
    timestamp: datetime,
    agent: str,
    environment: str,
    session_id: int,
    reason: str | None = None,
    replaced_session_id: int | None = None,
) -> None:
    record: dict[str, Any] = {
        "timestamp": iso_z(timestamp),
        "agent": agent,
        "environment": environment,
        "session_id": session_id,
        "event": event,
    }
    if reason is not None:
        record["reason"] = reason
    if replaced_session_id is not None:
        record["replaced_session_id"] = replaced_session_id
    log_record(record)


def _ensure_storage_ready() -> None:
    store.init_schema()
