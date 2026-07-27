"""
Rules analysis table CRUD and listing.
"""

from __future__ import annotations

from typing import Any

from backend.log_encryption import decrypt_row_fields, encrypt_text

from .db import _connect


def rule_analysis_list_for_event(event_id: int) -> list[dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT analysis_id, event_id, rule_code, rule_score, details, hard_block "
            "FROM rules_analysis "
            "WHERE event_id = ? ORDER BY analysis_id ASC",
            (event_id,),
        )
        return [decrypt_row_fields(dict(r), ("details",)) for r in cur.fetchall()]


def rule_analysis_list_for_event_with_rule_meta(event_id: int) -> list[dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT a.analysis_id, a.event_id, a.rule_code, a.rule_score, a.details, "
            "a.hard_block, r.rule_type, r.weight, r.compute_class, r.is_hard_block "
            "FROM rules_analysis a LEFT JOIN rules r ON a.rule_code = r.rule_code "
            "WHERE a.event_id = ? ORDER BY a.analysis_id ASC",
            (event_id,),
        )
        return [decrypt_row_fields(dict(r), ("details",)) for r in cur.fetchall()]


def rule_analysis_create(
    event_id: int,
    rule_code: str,
    rule_score: float | None,
    details: str,
    hard_block: bool = False,
) -> int:
    encrypted_details = encrypt_text(details)
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO rules_analysis "
            "(event_id, rule_code, rule_score, details, hard_block) "
            "VALUES (?, ?, ?, ?, ?)",
            (event_id, rule_code, rule_score, encrypted_details, 1 if hard_block else 0),
        )
        return int(cur.lastrowid)


def rule_analysis_list_for_rule(rule_code: str, limit: int) -> list[dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT analysis_id, event_id, rule_code, rule_score, details, hard_block "
            "FROM rules_analysis "
            "WHERE rule_code = ? ORDER BY analysis_id DESC LIMIT ?",
            (rule_code, limit),
        )
        return [decrypt_row_fields(dict(r), ("details",)) for r in cur.fetchall()]


def rule_analysis_list_for_rule_with_rule_meta(rule_code: str, limit: int) -> list[dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT a.analysis_id, a.event_id, a.rule_code, a.rule_score, a.details, "
            "a.hard_block, r.rule_type, r.weight, r.compute_class, r.is_hard_block "
            "FROM rules_analysis a LEFT JOIN rules r ON a.rule_code = r.rule_code "
            "WHERE a.rule_code = ? ORDER BY a.analysis_id DESC LIMIT ?",
            (rule_code, limit),
        )
        return [decrypt_row_fields(dict(r), ("details",)) for r in cur.fetchall()]

