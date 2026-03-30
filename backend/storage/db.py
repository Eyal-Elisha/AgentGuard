"""
SQLite low-level helpers: path resolution, connections, datetime helpers.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator


def database_path() -> str:
    """
    Resolve the SQLite database file path.

    - If `DATABASE_URL=sqlite:///absolute/path/or/relative` is set, use it.
    - Otherwise, default to `backend/agentguard.db`.
    """
    if os.environ.get("DATABASE_URL"):
        url = os.environ["DATABASE_URL"]
        if url.startswith("sqlite:///"):
            path = url.replace("sqlite:///", "", 1)
            return path.replace("/", os.sep)
        return url

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(backend_dir, "agentguard.db")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(database_path(), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _dt_iso(dt: datetime) -> str:
    """
    Convert a datetime to a UTC ISO-8601 string suitable for SQLite storage.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

