"""Small event update helpers."""

from __future__ import annotations

from .db import _connect


def event_update_guard_action(event_id: int, guard_action: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE events SET guard_action = ? WHERE event_id = ?",
            (guard_action, event_id),
        )
        return cur.rowcount > 0
