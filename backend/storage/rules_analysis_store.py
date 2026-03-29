"""
Rules analysis table CRUD and listing.
"""

from __future__ import annotations

from typing import Any

from .db import _connect


def _fetch_rules_analysis_base(
    where_clause: str, 
    params: tuple, 
    order_by: str, 
    limit: int | None = None
) -> list[dict[str, Any]]:
    query = (
        "SELECT a.analysis_id, a.event_id, a.rule_code, a.rule_score, a.details, "
        "r.rule_type, r.weight "
        "FROM rules_analysis a "
        "LEFT JOIN rules r ON a.rule_code = r.rule_code "
        f"WHERE {where_clause} ORDER BY {order_by}"
    )
    if limit is not None:
        query += f" LIMIT {limit}"
        
    with _connect() as conn:
        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


def rule_analysis_list_for_event(event_id: int) -> list[dict[str, Any]]:
    return _fetch_rules_analysis_base(
        where_clause="a.event_id = ?",
        params=(event_id,),
        order_by="a.analysis_id ASC"
    )


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
        return int(cur.lastrowid)


def rule_analysis_list_for_rule(rule_code: str, limit: int) -> list[dict[str, Any]]:
    return _fetch_rules_analysis_base(
        where_clause="a.rule_code = ?",
        params=(rule_code,),
        order_by="a.analysis_id DESC",
        limit=limit
    )

