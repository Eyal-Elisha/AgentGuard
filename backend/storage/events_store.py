"""
Events table CRUD and listing filters.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .db import _connect, _dt_iso


def event_create(
    session_id: int,
    timestamp: datetime,
    url: str,
    guard_action: str,
    risk_score: float,
    http_method: str,
    headers_json: str,
) -> int:
    ts = _dt_iso(timestamp)
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO events (session_id, timestamp, url, guard_action, risk_score, http_method, headers_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, ts, url, guard_action, risk_score, http_method, headers_json),
        )
        conn.commit()
        return int(cur.lastrowid)


def event_get(event_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT event_id, session_id, timestamp, url, guard_action, risk_score, http_method, headers_json "
            "FROM events WHERE event_id = ?",
            (event_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def _event_filter_sql(
    base_where: list[str],
    params: list[Any],
    filters: dict[str, Any],
) -> tuple[list[str], list[Any]]:
    if filters.get("guard_action"):
        base_where.append("guard_action = ?")
        params.append(filters["guard_action"])
    if filters.get("min_risk_score") is not None:
        base_where.append("risk_score >= ?")
        params.append(filters["min_risk_score"])
    if filters.get("max_risk_score") is not None:
        base_where.append("risk_score <= ?")
        params.append(filters["max_risk_score"])
    if filters.get("from_timestamp") is not None:
        base_where.append("timestamp >= ?")
        params.append(_dt_iso(filters["from_timestamp"]))
    if filters.get("to_timestamp") is not None:
        base_where.append("timestamp <= ?")
        params.append(_dt_iso(filters["to_timestamp"]))
    return base_where, params


def events_list_for_session(
    session_id: int,
    filters: dict[str, Any],
    order: str = "ASC",
) -> list[dict[str, Any]]:
    where = ["session_id = ?"]
    params: list[Any] = [session_id]
    where, params = _event_filter_sql(where, params, filters)
    sql = (
        "SELECT event_id, session_id, timestamp, url, guard_action, risk_score, http_method, headers_json "
        f"FROM events WHERE {' AND '.join(where)} ORDER BY timestamp {order}"
    )
    with _connect() as conn:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def events_list_all(filters: dict[str, Any]) -> list[dict[str, Any]]:
    where = ["1=1"]
    params: list[Any] = []
    where, params = _event_filter_sql(where, params, filters)
    sql = (
        "SELECT event_id, session_id, timestamp, url, guard_action, risk_score, http_method, headers_json "
        f"FROM events WHERE {' AND '.join(where)} ORDER BY timestamp DESC"
    )
    with _connect() as conn:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

