"""Builds a `SessionContext` from stored session events. The only place the
analysis layer touches storage, which keeps the contextual rules pure
functions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from backend.analysis.rules import PriorEvent, SessionContext
from backend.storage import sqlite_store as store

_logger = logging.getLogger(__name__)


def _parse_iso_timestamp(value: str) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        # SQLite rows are written as `...Z`; convert to a tz-aware UTC datetime.
        cleaned = value.replace("Z", "+00:00") if value.endswith("Z") else value
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _host_from_url(url: str) -> str:
    if not url:
        return ""
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def _ensure_aware_utc(timestamp: Optional[datetime]) -> Optional[datetime]:
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def build_context(
    *,
    session_id: Optional[int],
    current_timestamp: Optional[datetime],
    current_url: str,
) -> SessionContext:
    """Return a populated `SessionContext` for the request being evaluated.

    Returns an empty context (with current request metadata only) when:
    - `session_id` is None (no audit context), or
    - storage lookup fails (fail-open for evaluation).
    """
    current_ts = _ensure_aware_utc(current_timestamp)
    current_host = _host_from_url(current_url)
    base = SessionContext(
        current_event_timestamp=current_ts,
        current_event_host=current_host,
    )

    if session_id is None:
        return base

    try:
        rows = store.events_list_for_session(
            int(session_id),
            filters={"to_timestamp": current_ts} if current_ts is not None else {},
            order="ASC",
        )
    except Exception:
        _logger.exception(
            "[AgentGuard] Failed to load prior events for session_id=%s; "
            "falling back to empty context",
            session_id,
        )
        return base

    prior: list[PriorEvent] = []
    for row in rows:
        ts = _parse_iso_timestamp(str(row.get("timestamp", "")))
        if ts is None:
            continue
        prior.append(
            PriorEvent(
                timestamp=ts,
                host=_host_from_url(str(row.get("url", ""))),
                guard_action=str(row.get("guard_action", "")),
                risk_score=float(row.get("risk_score") or 0.0),
            )
        )

    base.prior_events = prior
    return base
