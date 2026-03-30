"""
Database schema initialization.
"""

from __future__ import annotations

import sqlite3
from threading import Lock

from .db import _connect, database_path

_INIT_LOCK = Lock()
_INITIALIZED_DATABASES: set[str] = set()
_REQUIRED_TABLES = frozenset({"users", "sessions", "events", "rules", "rules_analysis"})


def _schema_exists() -> bool:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN (?, ?, ?, ?, ?)",
            tuple(sorted(_REQUIRED_TABLES)),
        ).fetchall()
    return {str(row["name"]) for row in rows} == _REQUIRED_TABLES


def init_schema() -> None:
    db_path = database_path()
    if db_path in _INITIALIZED_DATABASES:
        return
    if _schema_exists():
        _INITIALIZED_DATABASES.add(db_path)
        return

    with _INIT_LOCK:
        if db_path in _INITIALIZED_DATABASES:
            return
        if _schema_exists():
            _INITIALIZED_DATABASES.add(db_path)
            return
        with _connect() as conn:
            # WAL allows dashboard reads to coexist with proxy writes much more reliably.
            try:
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA synchronous = NORMAL")
            except sqlite3.OperationalError:
                # Another live process can temporarily block WAL negotiation; if the schema
                # already exists, startup should still proceed instead of crashing.
                if _schema_exists():
                    _INITIALIZED_DATABASES.add(db_path)
                    return
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        is_admin INTEGER NOT NULL CHECK (is_admin IN (0, 1)),
                        password_hash TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        environment TEXT NOT NULL,
                        agent_name TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS events (
                        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                        timestamp TEXT NOT NULL,
                        url TEXT NOT NULL,
                        guard_action TEXT NOT NULL,
                        risk_score REAL NOT NULL,
                        http_method TEXT,
                        headers_json TEXT
                    );
                    CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);

                    CREATE TABLE IF NOT EXISTS rules (
                        rule_code TEXT PRIMARY KEY,
                        weight REAL NOT NULL,
                        rule_type TEXT NOT NULL,
                        compute_class TEXT NOT NULL,
                        is_enabled INTEGER NOT NULL CHECK (is_enabled IN (0, 1)),
                        is_hard_block INTEGER NOT NULL CHECK (is_hard_block IN (0, 1)),
                        description TEXT
                    );

                    CREATE TABLE IF NOT EXISTS rules_analysis (
                        analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
                        rule_code TEXT NOT NULL REFERENCES rules(rule_code) ON DELETE CASCADE,
                        rule_score REAL,
                        details TEXT
                    );
                    CREATE INDEX IF NOT EXISTS idx_ra_event ON rules_analysis(event_id);
                    CREATE INDEX IF NOT EXISTS idx_ra_rule ON rules_analysis(rule_code);
                    """
                )
            except sqlite3.OperationalError:
                if _schema_exists():
                    _INITIALIZED_DATABASES.add(db_path)
                    return
                raise
        _INITIALIZED_DATABASES.add(db_path)

