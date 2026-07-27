"""
Events table CRUD and listing filters.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.log_encryption import decrypt_row_fields, encrypt_text

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
    encrypted_url = encrypt_text(url)
    encrypted_headers_json = encrypt_text(headers_json)
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO events (session_id, timestamp, url, guard_action, risk_score, http_method, headers_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                ts,
                encrypted_url,
                guard_action,
                risk_score,
                http_method,
                encrypted_headers_json,
            ),
        )
        return int(cur.lastrowid)


def event_get(event_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT event_id, session_id, timestamp, url, guard_action, risk_score, http_method, headers_json "
            "FROM events WHERE event_id = ?",
            (event_id,),
        )
        row = cur.fetchone()
        return decrypt_row_fields(dict(row), ("url", "headers_json")) if row else None


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
    if filters.get("user_id") is not None:
        base_where.append("s.user_id = ?")
        params.append(filters["user_id"])
    return base_where, params


def events_list_for_session(
    session_id: int,
    filters: dict[str, Any],
    order: str = "ASC",
) -> list[dict[str, Any]]:
    where = ["e.session_id = ?"]
    params: list[Any] = [session_id]
    where, params = _event_filter_sql(where, params, filters)
    sql = (
        "SELECT e.event_id, e.session_id, s.user_id, e.timestamp, e.url, e.guard_action, "
        "e.risk_score, e.http_method, e.headers_json "
        "FROM events e JOIN sessions s ON s.session_id = e.session_id "
        f"WHERE {' AND '.join(where)} ORDER BY e.timestamp {order}"
    )
    with _connect() as conn:
        cur = conn.execute(sql, params)
        return [decrypt_row_fields(dict(r), ("url", "headers_json")) for r in cur.fetchall()]


def events_list_all(filters: dict[str, Any]) -> list[dict[str, Any]]:
    where = ["1=1"]
    params: list[Any] = []
    where, params = _event_filter_sql(where, params, filters)
    sql = (
        "SELECT e.event_id, e.session_id, s.user_id, e.timestamp, e.url, e.guard_action, "
        "e.risk_score, e.http_method, e.headers_json "
        "FROM events e JOIN sessions s ON s.session_id = e.session_id "
        f"WHERE {' AND '.join(where)} ORDER BY e.timestamp DESC"
    )
    with _connect() as conn:
        cur = conn.execute(sql, params)
        return [decrypt_row_fields(dict(r), ("url", "headers_json")) for r in cur.fetchall()]

