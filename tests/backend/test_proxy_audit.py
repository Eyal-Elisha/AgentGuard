from __future__ import annotations

import json
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import create_app
from backend.analysis.rules import Decision, EvaluationResult, RuleResult, RuleType
from backend.proxy.audit import ensure_proxy_session_started
from backend.storage import sqlite_store as store


def _make_result(decision: Decision) -> EvaluationResult:
    return EvaluationResult(
        decision=decision,
        risk_score=0.82 if decision == Decision.BLOCK else 0.42,
        rule_results=[
            RuleResult(
                rule_id="sensitive_fields",
                rule_type=RuleType.DETERMINISTIC,
                score=1.0,
                hard_block=False,
                explanation="Sensitive fields present on page",
                triggered=True,
            ),
            RuleResult(
                rule_id="custom_blacklist",
                rule_type=RuleType.DETERMINISTIC,
                score=0.0,
                hard_block=True,
                explanation="Not found in custom local blacklist",
                triggered=False,
            ),
        ],
        hard_block_triggered=decision == Decision.BLOCK,
        stage_b_required=decision == Decision.WARN,
    )


class ProxyAuditRouteTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self.log_path = os.path.join(self.temp_dir.name, "agentguard_audit.jsonl")
        self._old_env = {
            "DATABASE_URL": os.environ.get("DATABASE_URL"),
            "JWT_SECRET": os.environ.get("JWT_SECRET"),
            "REQUIRE_AUTH": os.environ.get("REQUIRE_AUTH"),
            "AGENTGUARD_AUDIT_LOG_PATH": os.environ.get("AGENTGUARD_AUDIT_LOG_PATH"),
        }
        db_url_path = Path(self.db_path).resolve().as_posix()
        os.environ["DATABASE_URL"] = f"sqlite:///{db_url_path}"
        os.environ["JWT_SECRET"] = "test-secret"
        os.environ["REQUIRE_AUTH"] = "false"
        os.environ["AGENTGUARD_AUDIT_LOG_PATH"] = self.log_path

        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        audit_logger = logging.getLogger("agentguard.audit")
        for handler in list(audit_logger.handlers):
            audit_logger.removeHandler(handler)
            handler.close()
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def _payload(self, **overrides):
        payload = {
            "timestamp": "2026-03-29T22:30:00Z",
            "url": "https://example.com/login",
            "method": "POST",
            "headers": {"user-agent": "CursorAgent/1.0", "content-type": "application/json"},
            "body": "{\"prompt\":\"hello\"}",
            "environment": "test",
        }
        payload.update(overrides)
        return payload

    def test_proxy_decision_defaults_to_browseros_agent(self):
        with patch("backend.routes.proxy.evaluate_http_payload", return_value=_make_result(Decision.WARN)):
            response = self.client.post("/api/proxy/decision", json=self._payload())

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        audit = body["audit"]
        self.assertEqual(body["decision"], "warn")
        self.assertEqual(audit["agent"], "browserOS")
        self.assertEqual(audit["environment"], "test")
        self.assertEqual(audit["decision"], "warn")
        self.assertEqual(audit["risk_score"], 0.42)

        session = store.session_get(audit["session_id"])
        self.assertIsNotNone(session)
        self.assertEqual(session["agent_name"], "browserOS")
        self.assertEqual(session["environment"], "test")

        event = store.event_get(audit["event_id"])
        self.assertIsNotNone(event)
        self.assertEqual(event["session_id"], audit["session_id"])
        self.assertEqual(event["guard_action"], "Warn")
        self.assertEqual(event["http_method"], "POST")
        self.assertEqual(event["url"], "https://example.com/login")

        analyses = store.rule_analysis_list_for_event(audit["event_id"])
        self.assertEqual(len(analyses), 2)
        self.assertEqual({item["rule_code"] for item in analyses}, {"sensitive_fields", "custom_blacklist"})
        self.assertIsNotNone(store.rule_get("sensitive_fields"))
        self.assertIsNotNone(store.rule_get("custom_blacklist"))

        log_lines = Path(self.log_path).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(log_lines), 1)
        log_entry = json.loads(log_lines[0])
        self.assertEqual(log_entry["session_id"], audit["session_id"])
        self.assertEqual(log_entry["event_id"], audit["event_id"])
        self.assertEqual(log_entry["timestamp"], "2026-03-29T22:30:00Z")
        self.assertEqual(log_entry["agent"], "browserOS")
        self.assertEqual(log_entry["url"], "https://example.com/login")
        self.assertEqual(log_entry["risk_score"], 0.42)
        self.assertEqual(log_entry["decision"], "warn")

    def test_proxy_decision_reuses_open_session_for_same_agent(self):
        with patch("backend.routes.proxy.evaluate_http_payload", return_value=_make_result(Decision.ALLOW)):
            first = self.client.post("/api/proxy/decision", json=self._payload(timestamp="2026-03-29T22:30:00Z"))
            second = self.client.post("/api/proxy/decision", json=self._payload(timestamp="2026-03-29T22:31:00Z"))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        first_audit = first.get_json()["audit"]
        second_audit = second.get_json()["audit"]
        self.assertEqual(first_audit["session_id"], second_audit["session_id"])
        self.assertNotEqual(first_audit["event_id"], second_audit["event_id"])
        self.assertEqual(len(store.sessions_list_desc()), 1)

    def test_proxy_start_creates_browseros_session_used_by_decisions(self):
        started = ensure_proxy_session_started(environment="test")
        self.assertTrue(started["created"])
        self.assertEqual(started["agent"], "browserOS")

        with patch("backend.routes.proxy.evaluate_http_payload", return_value=_make_result(Decision.ALLOW)):
            response = self.client.post("/api/proxy/decision", json=self._payload(timestamp="2026-03-29T22:32:00Z"))

        self.assertEqual(response.status_code, 200)
        audit = response.get_json()["audit"]
        self.assertEqual(audit["session_id"], started["session_id"])
        self.assertEqual(audit["agent"], "browserOS")

    def test_proxy_start_rotates_to_new_session_id(self):
        first = ensure_proxy_session_started(environment="test")
        second = ensure_proxy_session_started(environment="test")

        self.assertTrue(first["created"])
        self.assertTrue(second["created"])
        self.assertNotEqual(first["session_id"], second["session_id"])
        self.assertEqual(second["replaced_session_id"], first["session_id"])

        first_session = store.session_get(first["session_id"])
        second_session = store.session_get(second["session_id"])
        self.assertIsNotNone(first_session)
        self.assertIsNotNone(second_session)
        self.assertIsNotNone(first_session["end_time"])
        self.assertIsNone(second_session["end_time"])

        log_lines = Path(self.log_path).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(log_lines), 3)
        first_started = json.loads(log_lines[0])
        closed = json.loads(log_lines[1])
        second_started = json.loads(log_lines[2])
        self.assertEqual(first_started["event"], "proxy_session_started")
        self.assertEqual(closed["event"], "proxy_session_closed")
        self.assertEqual(closed["session_id"], first["session_id"])
        self.assertEqual(closed["reason"], "superseded_by_new_proxy_session")
        self.assertEqual(second_started["event"], "proxy_session_started")
        self.assertEqual(second_started["session_id"], second["session_id"])
        self.assertEqual(second_started["replaced_session_id"], first["session_id"])

    def test_proxy_start_bootstraps_schema_without_flask_app(self):
        audit_logger = logging.getLogger("agentguard.audit")
        for handler in list(audit_logger.handlers):
            audit_logger.removeHandler(handler)
            handler.close()

        self.app = None
        self.client = None

        started = ensure_proxy_session_started(environment="test")

        self.assertEqual(started["agent"], "browserOS")
        self.assertEqual(started["environment"], "test")
        stored = store.session_get(started["session_id"])
        self.assertIsNotNone(stored)
        self.assertEqual(stored["agent_name"], "browserOS")
        log_lines = Path(self.log_path).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(log_lines), 1)
        log_entry = json.loads(log_lines[0])
        self.assertEqual(log_entry["event"], "proxy_session_started")
        self.assertEqual(log_entry["session_id"], started["session_id"])

    def test_proxy_decision_rejects_unknown_session_id(self):
        with patch("backend.routes.proxy.evaluate_http_payload", return_value=_make_result(Decision.ALLOW)):
            response = self.client.post("/api/proxy/decision", json=self._payload(session_id=999))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {"error": "Provided session_id does not reference an existing session"},
        )

    def test_proxy_decision_rejects_mismatched_session_environment(self):
        started = ensure_proxy_session_started(environment="test")

        with patch("backend.routes.proxy.evaluate_http_payload", return_value=_make_result(Decision.ALLOW)):
            response = self.client.post(
                "/api/proxy/decision",
                json=self._payload(session_id=started["session_id"], environment="prod"),
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {"error": "Provided environment does not match the referenced session"},
        )


if __name__ == "__main__":
    unittest.main()
