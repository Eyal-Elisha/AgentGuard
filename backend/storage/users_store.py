"""
Users table CRUD.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from .db import _connect


class UsernameTakenError(Exception):
    """Raised when INSERT violates users.username uniqueness (including race conditions)."""


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
        try:
            cur = conn.execute(
                "INSERT INTO users (username, is_admin, password_hash) VALUES (?, ?, ?)",
                (username, 1 if is_admin else 0, password_hash),
            )
        except sqlite3.IntegrityError as exc:
            raise UsernameTakenError from exc
        return int(cur.lastrowid)


def user_get(user_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT user_id, username, is_admin FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

