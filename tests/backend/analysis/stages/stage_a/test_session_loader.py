"""Tests for the session loader bridging SQLite events into a SessionContext."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.fernet import Fernet

from backend.analysis.stages.stage_a.session_loader import build_context
from backend.storage import sqlite_store as store


class SessionLoaderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "session_loader.db")
        self._old_db_url = os.environ.get("DATABASE_URL")
        self._old_log_encryption_key = os.environ.get("AGENTGUARD_LOG_ENCRYPTION_KEY")
        db_url_path = Path(self.db_path).resolve().as_posix()
        os.environ["DATABASE_URL"] = f"sqlite:///{db_url_path}"
        os.environ["AGENTGUARD_LOG_ENCRYPTION_KEY"] = Fernet.generate_key().decode("utf-8")
        store.init_schema()

        self.session_id = store.session_create(
            user_id=None,
            start_time=datetime(2026, 5, 17, 9, 0, 0, tzinfo=timezone.utc),
            environment="test",
            agent_name="BrowserOS",
        )

    def tearDown(self) -> None:
        if self._old_db_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self._old_db_url
        if self._old_log_encryption_key is None:
            os.environ.pop("AGENTGUARD_LOG_ENCRYPTION_KEY", None)
        else:
            os.environ["AGENTGUARD_LOG_ENCRYPTION_KEY"] = self._old_log_encryption_key
        self.temp_dir.cleanup()

    def _insert_event(
        self,
        seconds_after_start: float,
        url: str,
        guard_action: str,
        risk_score: float = 0.0,
    ) -> int:
        ts = datetime(2026, 5, 17, 9, 0, 0, tzinfo=timezone.utc) + timedelta(
            seconds=seconds_after_start
        )
        return store.event_create(
            session_id=self.session_id,
            timestamp=ts,
            url=url,
            guard_action=guard_action,
            risk_score=risk_score,
            http_method="GET",
            headers_json="{}",
        )

    def test_returns_empty_context_when_session_id_is_none(self):
        ctx = build_context(
            session_id=None,
            current_timestamp=datetime(2026, 5, 17, 9, 0, 30, tzinfo=timezone.utc),
            current_url="https://example.com/page",
        )
        self.assertEqual(ctx.prior_events, [])
        self.assertEqual(ctx.current_event_host, "example.com")

    def test_loads_prior_events_in_ascending_order(self):
        self._insert_event(10, "https://b.com/x", "Allow", 0.1)
        self._insert_event(5, "https://a.com/x", "Warn", 0.5)
        self._insert_event(20, "https://c.com/x", "Block", 0.9)

        current_ts = datetime(2026, 5, 17, 9, 0, 30, tzinfo=timezone.utc)
        ctx = build_context(
            session_id=self.session_id,
            current_timestamp=current_ts,
            current_url="https://target.com/page",
        )

        self.assertEqual(len(ctx.prior_events), 3)
        hosts = [e.host for e in ctx.prior_events]
        self.assertEqual(hosts, ["a.com", "b.com", "c.com"])
        self.assertEqual(ctx.prior_events[0].guard_action, "Warn")
        self.assertEqual(ctx.prior_events[2].guard_action, "Block")
        # Timestamps are tz-aware UTC and strictly ascending.
        self.assertTrue(
            ctx.prior_events[0].timestamp
            < ctx.prior_events[1].timestamp
            < ctx.prior_events[2].timestamp
        )
        for event in ctx.prior_events:
            self.assertEqual(event.timestamp.tzinfo, timezone.utc)

    def test_excludes_events_after_current_timestamp(self):
        self._insert_event(5, "https://past.com/x", "Allow")
        self._insert_event(60, "https://future.com/x", "Warn")

        current_ts = datetime(2026, 5, 17, 9, 0, 30, tzinfo=timezone.utc)
        ctx = build_context(
            session_id=self.session_id,
            current_timestamp=current_ts,
            current_url="https://target.com/page",
        )

        self.assertEqual(len(ctx.prior_events), 1)
        self.assertEqual(ctx.prior_events[0].host, "past.com")

    def test_extracts_lowercase_host_from_current_url(self):
        ctx = build_context(
            session_id=self.session_id,
            current_timestamp=datetime(2026, 5, 17, 9, 0, 30, tzinfo=timezone.utc),
            current_url="https://Target.Example.COM:8080/path?q=1",
        )
        self.assertEqual(ctx.current_event_host, "target.example.com")

    def test_handles_no_current_timestamp(self):
        self._insert_event(5, "https://a.com/x", "Warn")
        ctx = build_context(
            session_id=self.session_id,
            current_timestamp=None,
            current_url="https://target.com/page",
        )
        # With no upper-bound filter, all events come back.
        self.assertEqual(len(ctx.prior_events), 1)
        self.assertEqual(ctx.prior_events[0].host, "a.com")

    def test_naive_timestamp_is_treated_as_utc(self):
        self._insert_event(5, "https://a.com/x", "Warn")
        ctx = build_context(
            session_id=self.session_id,
            current_timestamp=datetime(2026, 5, 17, 9, 0, 30),  # naive
            current_url="https://target.com/page",
        )
        self.assertEqual(len(ctx.prior_events), 1)
        self.assertEqual(ctx.current_event_timestamp.tzinfo, timezone.utc)


if __name__ == "__main__":
    unittest.main()
