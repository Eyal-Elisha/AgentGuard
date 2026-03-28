"""
Rules table CRUD.
"""

from __future__ import annotations

from typing import Any

from .db import _connect


def rules_list_asc() -> list[dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT rule_code, weight, rule_type, compute_class, is_enabled, is_hard_block, description "
            "FROM rules ORDER BY rule_code ASC"
        )
        return [dict(r) for r in cur.fetchall()]


def rule_get(rule_code: str) -> dict[str, Any] | None:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT rule_code, weight, rule_type, compute_class, is_enabled, is_hard_block, description "
            "FROM rules WHERE rule_code = ?",
            (rule_code,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def rule_create(
    rule_code: str,
    weight: float,
    rule_type: str,
    compute_class: str,
    is_enabled: bool,
    is_hard_block: bool,
    description: str | None,
) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO rules (rule_code, weight, rule_type, compute_class, is_enabled, is_hard_block, description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                rule_code,
                weight,
                rule_type,
                compute_class,
                1 if is_enabled else 0,
                1 if is_hard_block else 0,
                description,
            ),
        )
        conn.commit()

