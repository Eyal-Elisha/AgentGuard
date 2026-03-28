"""Shared Flask client + temp SQLite DB for backend API integration tests."""

import os
import tempfile
import unittest

from backend import create_app


class BackendApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self._old_env = {
            "DATABASE_URL": os.environ.get("DATABASE_URL"),
            "JWT_SECRET": os.environ.get("JWT_SECRET"),
            "REQUIRE_AUTH": os.environ.get("REQUIRE_AUTH"),
        }
        os.environ["DATABASE_URL"] = f"sqlite:///{self.db_path}"
        os.environ["JWT_SECRET"] = "test-secret"
        os.environ["REQUIRE_AUTH"] = "false"

        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def create_session(self, **overrides):
        payload = {
            "start_time": "2026-03-25T12:00:00Z",
            "agent_name": "agent-1",
            "environment": "test",
        }
        payload.update(overrides)
        return self.client.post("/sessions", json=payload)

    def create_event(self, session_id: int, **overrides):
        payload = {
            "url": "https://example.test/api",
            "headers": {"x-test": "1"},
            "method": "GET",
            "timestamp": "2026-03-25T12:00:00Z",
            "guard_action": "Allow",
            "risk_score": 0.2,
        }
        payload.update(overrides)
        return self.client.post(f"/sessions/{session_id}/events", json=payload)

    def create_rule(self, **overrides):
        payload = {
            "rule_code": "R001",
            "weight": 0.7,
            "rule_type": "deterministic",
            "compute_class": "cheap",
            "is_enabled": True,
            "is_hard_block": False,
            "description": "Rule description",
        }
        payload.update(overrides)
        return self.client.post("/rules", json=payload)
