"""Database reads for session risk scoring."""

from __future__ import annotations

from typing import Any

from backend.storage.db import _connect

from .constants import SENSITIVE_RULE_CODES
from .models import EventRiskPoint, SessionRiskInputs


def _event_points(rows: list[dict[str, Any]]) -> list[EventRiskPoint]:
    return [
        EventRiskPoint(
            event_id=int(row["event_id"]),
            timestamp=str(row["timestamp"]),
            risk_score=float(row["risk_score"]),
            guard_action=str(row["guard_action"]),
        )
        for row in rows
    ]


def load_session_risk_inputs(session_id: int) -> SessionRiskInputs:
    placeholders = ",".join("?" for _ in SENSITIVE_RULE_CODES)
    sensitive_params: tuple[Any, ...] = (*sorted(SENSITIVE_RULE_CODES), session_id)

    with _connect() as conn:
        event_rows = conn.execute(
            "SELECT event_id, timestamp, risk_score, guard_action "
            "FROM events WHERE session_id = ? ORDER BY timestamp ASC, event_id ASC",
            (session_id,),
        ).fetchall()

        sensitive_count = conn.execute(
            "SELECT COUNT(*) AS c FROM rules_analysis a "
            "JOIN events e ON e.event_id = a.event_id "
            f"WHERE a.rule_code IN ({placeholders}) "
            "AND COALESCE(a.rule_score, 0) > 0 AND e.session_id = ?",
            sensitive_params,
        ).fetchone()["c"]

        hard_block_count = conn.execute(
            "SELECT COUNT(*) AS c FROM rules_analysis a "
            "JOIN rules r ON r.rule_code = a.rule_code "
            "JOIN events e ON e.event_id = a.event_id "
            "WHERE r.is_hard_block = 1 "
            "AND COALESCE(a.rule_score, 0) > 0 AND e.session_id = ?",
            (session_id,),
        ).fetchone()["c"]

    return SessionRiskInputs(
        events=_event_points([dict(row) for row in event_rows]),
        sensitive_interaction_count=int(sensitive_count),
        hard_block_count=int(hard_block_count),
    )
