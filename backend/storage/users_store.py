"""
Users table CRUD.
"""

from __future__ import annotations

from typing import Any

from .db import _connect


def user_get_by_username(username: str) -> dict[str, Any] | None:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT user_id, username, is_admin, password_hash FROM users WHERE username = ?",
            (username,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def user_create(username: str, password_hash: str, is_admin: bool = False) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, is_admin, password_hash) VALUES (?, ?, ?)",
            (username, 1 if is_admin else 0, password_hash),
        )
        conn.commit()
        return int(cur.lastrowid)

