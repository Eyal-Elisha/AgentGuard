"""
Rules analysis table CRUD and listing.
"""

from __future__ import annotations

from typing import Any

from .db import _connect


def rule_analysis_list_for_event(event_id: int) -> list[dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT analysis_id, event_id, rule_code, rule_score, details FROM rules_analysis "
            "WHERE event_id = ? ORDER BY analysis_id ASC",
            (event_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def rule_analysis_create(
    event_id: int,
    rule_code: str,
    rule_score: float | None,
    details: str,
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO rules_analysis (event_id, rule_code, rule_score, details) VALUES (?, ?, ?, ?)",
            (event_id, rule_code, rule_score, details),
        )
        conn.commit()
        return int(cur.lastrowid)


def rule_analysis_list_for_rule(rule_code: str, limit: int) -> list[dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT analysis_id, event_id, rule_code, rule_score, details FROM rules_analysis "
            "WHERE rule_code = ? ORDER BY analysis_id DESC LIMIT ?",
            (rule_code, limit),
        )
        return [dict(r) for r in cur.fetchall()]

