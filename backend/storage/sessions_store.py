"""
Sessions table CRUD and stats.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from .db import _connect, _dt_iso


def sessions_list_desc() -> list[dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT session_id, user_id, start_time, end_time, environment, agent_name "
            "FROM sessions ORDER BY session_id DESC"
        )
        return [dict(r) for r in cur.fetchall()]


def session_get(session_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT session_id, user_id, start_time, end_time, environment, agent_name "
            "FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def session_create(
    user_id: int | None,
    start_time: datetime,
    environment: str,
    agent_name: str,
) -> int:
    st = _dt_iso(start_time)
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (user_id, start_time, end_time, environment, agent_name) "
            "VALUES (?, ?, NULL, ?, ?)",
            (user_id, st, environment, agent_name),
        )
        return int(cur.lastrowid)


def session_update_end(session_id: int, end_time: datetime) -> None:
    et = _dt_iso(end_time)
    with _connect() as conn:
        conn.execute("UPDATE sessions SET end_time = ? WHERE session_id = ?", (et, session_id))


def session_try_close(
    session_id: int, end_time: datetime
) -> Literal["closed", "not_found", "already_closed"]:
    et = _dt_iso(end_time)
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE sessions SET end_time = ? WHERE session_id = ? AND end_time IS NULL",
            (et, session_id),
        )
        if cur.rowcount > 0:
            return "closed"
    if session_get(session_id) is None:
        return "not_found"
    return "already_closed"


def session_delete(session_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        return cur.rowcount > 0


def session_stats(session_id: int) -> dict[str, Any] | None:
    """Returns None if session does not exist."""
    if session_get(session_id) is None:
        return None
    with _connect() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE session_id = ?", (session_id,)
        ).fetchone()["c"]
        allow = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE session_id = ? AND guard_action = 'Allow'",
            (session_id,),
        ).fetchone()["c"]
        warn = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE session_id = ? AND guard_action = 'Warn'",
            (session_id,),
        ).fetchone()["c"]
        block = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE session_id = ? AND guard_action = 'Block'",
            (session_id,),
        ).fetchone()["c"]
        avg_row = conn.execute(
            "SELECT AVG(risk_score) AS a FROM events WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        avg = avg_row["a"]
        return {
            "total_events": int(total),
            "allow": int(allow),
            "warn": int(warn),
            "block": int(block),
            "average_risk_score": float(avg) if avg is not None else 0.0,
        }

