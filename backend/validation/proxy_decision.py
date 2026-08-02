"""Parsing the optional fields of a `POST /api/proxy/decision` body.

`validate_proxy_payload` has already checked the four fields the proxy must
send (url, method, headers, body). What is left are the four it may omit —
timestamp, environment, session_id and agent_name — each of which has a
default, and each of which is rejected outright if present but malformed.

Whether a field was *provided* matters downstream: an explicit environment or
agent name has to agree with the session it is being attributed to, while an
omitted one is simply inherited from that session.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .common import ALLOWED_ENVIRONMENTS, parse_iso_datetime, parse_positive_int

DEFAULT_ENVIRONMENT = "prod"


@dataclass(frozen=True)
class DecisionRequest:
    """One validated decision request, ready to evaluate."""

    url: str
    method: str
    headers: dict[str, str]
    body: bytes
    timestamp: datetime
    environment: str
    session_id: int | None
    agent_name: str | None
    environment_was_provided: bool
    agent_name_was_provided: bool


def parse_decision_request(payload: dict[str, Any]) -> DecisionRequest:
    """Build a `DecisionRequest`, raising ValueError on a malformed field."""
    return DecisionRequest(
        url=payload["url"],
        method=payload["method"].upper(),
        headers=payload["headers"],
        body=payload["body"].encode("utf-8", errors="replace"),
        timestamp=_timestamp(payload),
        environment=parse_environment(payload),
        session_id=_session_id(payload),
        agent_name=parse_agent_name(payload),
        environment_was_provided=payload.get("environment") is not None,
        agent_name_was_provided=payload.get("agent_name") is not None,
    )


def _timestamp(payload: dict[str, Any]) -> datetime:
    raw = payload.get("timestamp")
    if raw is None:
        return datetime.now(timezone.utc)
    parsed = parse_iso_datetime(raw)
    if parsed is None:
        raise ValueError("'timestamp' must be a valid ISO-8601 datetime")
    return parsed


def parse_environment(payload: dict[str, Any]) -> str:
    raw = payload.get("environment")
    if raw is None:
        return DEFAULT_ENVIRONMENT
    if not isinstance(raw, str) or raw.strip().lower() not in ALLOWED_ENVIRONMENTS:
        raise ValueError("'environment' must be one of: prod, test")
    return raw.strip().lower()


def _session_id(payload: dict[str, Any]) -> int | None:
    raw = payload.get("session_id")
    if raw is None:
        return None
    parsed = parse_positive_int(raw)
    if parsed is None:
        raise ValueError("'session_id' must be a positive integer")
    return parsed


def parse_agent_name(payload: dict[str, Any]) -> str | None:
    raw = payload.get("agent_name")
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("'agent_name' must be a non-empty string when provided")
    return raw.strip()
