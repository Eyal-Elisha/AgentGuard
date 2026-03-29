"""
Database schema initialization.
"""

from __future__ import annotations

from .db import _connect


def init_schema() -> None:
    with _connect() as conn:
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

