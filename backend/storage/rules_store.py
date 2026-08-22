"""
Rules table CRUD.
"""

from __future__ import annotations

from typing import Any

from .db import _connect


def rules_seed_defaults(rule_definitions: list[Any]) -> None:
    """Insert missing built-in rules without overwriting dashboard settings."""
    rows = [
        (
            rule.rule_id,
            rule.weight,
            rule.rule_type.value,
            rule.compute_class.value,
            1,
            1 if rule.hard_block else 0,
            rule.description,
        )
        for rule in rule_definitions
    ]
    with _connect() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO rules "
            "(rule_code, weight, rule_type, compute_class, is_enabled, is_hard_block, description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )


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


def rule_sync_metadata(
    rule_code: str,
    weight: float,
    rule_type: str,
    compute_class: str,
    is_hard_block: bool,
    description: str | None,
) -> bool:
    """Bring a rule's code-owned columns back in line with the catalogue.

    Rules are inserted the first time they run and were never updated after,
    so recalibrating a weight or demoting a rule from hard-blocking left the
    database describing the engine as it used to be. The dashboard reads these
    columns, so it kept showing the old numbers.

    `is_enabled` is deliberately not touched: that column belongs to the
    operator, who can toggle a rule from the dashboard, and the catalogue has
    no opinion about it.

    Returns True when a row was actually changed.
    """
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE rules SET weight = ?, rule_type = ?, compute_class = ?, "
            "is_hard_block = ?, description = ? "
            "WHERE rule_code = ? AND ("
            "  weight IS NOT ? OR rule_type IS NOT ? OR compute_class IS NOT ? "
            "  OR is_hard_block IS NOT ? OR description IS NOT ?)",
            (
                weight, rule_type, compute_class, 1 if is_hard_block else 0, description,
                rule_code,
                weight, rule_type, compute_class, 1 if is_hard_block else 0, description,
            ),
        )
        return cursor.rowcount > 0


def rule_set_enabled(rule_code: str, is_enabled: bool) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE rules SET is_enabled = ? WHERE rule_code = ?",
            (1 if is_enabled else 0, rule_code),
        )
        return cur.rowcount > 0
