from __future__ import annotations

import json
import logging
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet

from backend import create_app
from backend.analysis.rules import Decision, EvaluationResult, RuleResult, RuleType
from backend.log_encryption import ENCRYPTED_VALUE_PREFIX, decrypt_text
from backend.proxy.audit import ensure_proxy_session_started, normalize_proxy_agent_name
from backend.storage import sqlite_store as store
from backend.validation.proxy_requests import (
    MAX_BODY_BYTES,
    MAX_PROXY_ENVELOPE_BYTES,
    validate_proxy_payload,
)


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


def _make_contextual_result() -> EvaluationResult:
    """Evaluation result that includes a triggered contextual rule."""
    return EvaluationResult(
        decision=Decision.WARN,
        risk_score=0.55,
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
                rule_id="previously_warned_domain_in_session",
                rule_type=RuleType.CONTEXTUAL,
                score=0.4,
                hard_block=False,
                explanation="2 visit(s) to previously warned domain(s) ['evil.com'] (Nmax=5)",
                triggered=True,
            ),
        ],
        hard_block_triggered=False,
        stage_b_required=True,
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
            "AGENTGUARD_LOG_ENCRYPTION_KEY": os.environ.get("AGENTGUARD_LOG_ENCRYPTION_KEY"),
        }
        db_url_path = Path(self.db_path).resolve().as_posix()
        os.environ["DATABASE_URL"] = f"sqlite:///{db_url_path}"
        os.environ["JWT_SECRET"] = "test-secret"
        os.environ["REQUIRE_AUTH"] = "false"
        os.environ["AGENTGUARD_AUDIT_LOG_PATH"] = self.log_path
        os.environ["AGENTGUARD_LOG_ENCRYPTION_KEY"] = Fernet.generate_key().decode("utf-8")

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

    def _audit_log_records(self) -> list[dict]:
        return [
            json.loads(decrypt_text(line))
            for line in Path(self.log_path).read_text(encoding="utf-8").splitlines()
        ]

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

    def test_hard_block_column_records_the_rule_that_actually_blocked(self):
        """The column must separate "did block here" from "may block".

        Recording the capability set it for every hard-block-capable rule on
        every event, so the events view reported a hard block on pages where
        no rule fired at all.
        """
        ensure_proxy_session_started(environment="test")
        blocked = EvaluationResult(
            decision=Decision.BLOCK,
            risk_score=1.0,
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
                    score=1.0,
                    hard_block=True,
                    explanation="Host is on the custom local blacklist",
                    triggered=True,
                ),
            ],
            hard_block_triggered=True,
            stage_b_required=False,
        )

        with patch("backend.routes.proxy.evaluate_http_payload", return_value=blocked):
            response = self.client.post("/api/proxy/decision", json=self._payload())

        self.assertEqual(response.status_code, 200)
        audit = response.get_json()["audit"]
        analyses = store.rule_analysis_list_for_event(audit["event_id"])
        by_code = {item["rule_code"]: item for item in analyses}
        self.assertEqual(by_code["custom_blacklist"]["hard_block"], 1)
        self.assertEqual(by_code["sensitive_fields"]["hard_block"], 0)

    def test_proxy_decision_defaults_to_the_catch_all_agent(self):
        started = ensure_proxy_session_started(environment="test")

        with patch("backend.routes.proxy.evaluate_http_payload", return_value=_make_result(Decision.WARN)):
            response = self.client.post("/api/proxy/decision", json=self._payload())

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        audit = body["audit"]
        self.assertEqual(body["decision"], "warn")
        self.assertEqual(audit["agent"], "AllTraffic")
        self.assertEqual(audit["environment"], "test")
        self.assertEqual(audit["decision"], "warn")
        self.assertEqual(audit["risk_score"], 0.42)
        self.assertEqual(audit["session_id"], started["session_id"])

        session = store.session_get(audit["session_id"])
        self.assertIsNotNone(session)
        self.assertEqual(session["agent_name"], "AllTraffic")
        self.assertEqual(session["environment"], "test")

        event = store.event_get(audit["event_id"])
        self.assertIsNotNone(event)
        self.assertEqual(event["session_id"], audit["session_id"])
        self.assertEqual(event["guard_action"], "Warn")
        self.assertEqual(event["http_method"], "POST")
        self.assertEqual(event["url"], "https://example.com/login")
        self.assertEqual(event["risk_score"], 0.42)

        analyses = store.rule_analysis_list_for_event(audit["event_id"])
        self.assertEqual(len(analyses), 2)
        self.assertEqual({item["rule_code"] for item in analyses}, {"sensitive_fields", "custom_blacklist"})
        sensitive_analysis = next(item for item in analyses if item["rule_code"] == "sensitive_fields")
        blacklist_analysis = next(item for item in analyses if item["rule_code"] == "custom_blacklist")
        self.assertEqual(sensitive_analysis["hard_block"], 0)
        self.assertEqual(sensitive_analysis["rule_score"], 1.0)
        # custom_blacklist is *able* to hard-block, but this fixture has it
        # scoring 0.0 and not triggering ("Not found in custom local
        # blacklist"), so it did not hard-block this request. The column records
        # what happened here, not what the rule is permitted to do; storing the
        # capability set it on every event and made the dashboard report a hard
        # block on pages where nothing fired.
        self.assertEqual(blacklist_analysis["hard_block"], 0)
        self.assertEqual(blacklist_analysis["rule_score"], 0.0)
        self.assertIsNotNone(store.rule_get("sensitive_fields"))
        self.assertIsNotNone(store.rule_get("custom_blacklist"))

        conn = sqlite3.connect(self.db_path)
        try:
            raw_event = conn.execute(
                "SELECT url, risk_score, headers_json FROM events WHERE event_id = ?",
                (audit["event_id"],),
            ).fetchone()
            raw_analyses = conn.execute(
                "SELECT rule_score, details FROM rules_analysis WHERE event_id = ?",
                (audit["event_id"],),
            ).fetchall()
        finally:
            conn.close()
        self.assertTrue(raw_event[0].startswith(ENCRYPTED_VALUE_PREFIX))
        self.assertTrue(raw_event[1].startswith(ENCRYPTED_VALUE_PREFIX))
        self.assertTrue(raw_event[2].startswith(ENCRYPTED_VALUE_PREFIX))
        self.assertNotIn("https://example.com/login", raw_event[0])
        self.assertNotIn("0.42", raw_event[1])
        self.assertTrue(all(row[0].startswith(ENCRYPTED_VALUE_PREFIX) for row in raw_analyses))
        self.assertTrue(all(row[1].startswith(ENCRYPTED_VALUE_PREFIX) for row in raw_analyses))
        self.assertTrue(all("Sensitive fields present on page" not in row[1] for row in raw_analyses))

        raw_log_lines = Path(self.log_path).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(raw_log_lines), 2)
        self.assertTrue(all(line.startswith(ENCRYPTED_VALUE_PREFIX) for line in raw_log_lines))
        self.assertNotIn("https://example.com/login", "\n".join(raw_log_lines))
        log_records = self._audit_log_records()
        self.assertEqual(log_records[0]["event"], "proxy_session_started")
        log_entry = log_records[1]
        self.assertEqual(log_entry["session_id"], audit["session_id"])
        self.assertEqual(log_entry["event_id"], audit["event_id"])
        self.assertEqual(log_entry["timestamp"], "2026-03-29T22:30:00Z")
        self.assertEqual(log_entry["agent"], "AllTraffic")
        self.assertEqual(log_entry["url"], "https://example.com/login")
        self.assertEqual(log_entry["risk_score"], 0.42)
        self.assertEqual(log_entry["decision"], "warn")

    def test_proxy_decision_reuses_open_session_for_same_agent(self):
        started = ensure_proxy_session_started(environment="test")

        with patch("backend.routes.proxy.evaluate_http_payload", return_value=_make_result(Decision.ALLOW)):
            first = self.client.post("/api/proxy/decision", json=self._payload(timestamp="2026-03-29T22:30:00Z"))
            second = self.client.post("/api/proxy/decision", json=self._payload(timestamp="2026-03-29T22:31:00Z"))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        first_audit = first.get_json()["audit"]
        second_audit = second.get_json()["audit"]
        self.assertEqual(first_audit["session_id"], started["session_id"])
        self.assertEqual(first_audit["session_id"], second_audit["session_id"])
        self.assertNotEqual(first_audit["event_id"], second_audit["event_id"])
        self.assertEqual(len(store.sessions_list_desc()), 1)

    def test_proxy_start_creates_default_session_used_by_decisions(self):
        started = ensure_proxy_session_started(environment="test")
        self.assertTrue(started["created"])
        self.assertEqual(started["agent"], "AllTraffic")

        with patch("backend.routes.proxy.evaluate_http_payload", return_value=_make_result(Decision.ALLOW)):
            response = self.client.post("/api/proxy/decision", json=self._payload(timestamp="2026-03-29T22:32:00Z"))

        self.assertEqual(response.status_code, 200)
        audit = response.get_json()["audit"]
        self.assertEqual(audit["session_id"], started["session_id"])
        self.assertEqual(audit["agent"], "AllTraffic")

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

        log_records = self._audit_log_records()
        self.assertEqual(len(log_records), 3)
        first_started = log_records[0]
        closed = log_records[1]
        second_started = log_records[2]
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

        self.assertEqual(started["agent"], "AllTraffic")
        self.assertEqual(started["environment"], "test")
        stored = store.session_get(started["session_id"])
        self.assertIsNotNone(stored)
        self.assertEqual(stored["agent_name"], "AllTraffic")
        log_records = self._audit_log_records()
        self.assertEqual(len(log_records), 1)
        log_entry = log_records[0]
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

    def test_proxy_decision_database_errors_return_503_and_log(self):
        with (
            patch(
                "backend.routes.proxy.store.session_get",
                side_effect=sqlite3.OperationalError("database is locked"),
            ),
            self.assertLogs("agentguard.api", level="ERROR") as logs,
        ):
            response = self.client.post("/api/proxy/decision", json=self._payload(session_id=1))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json(), {"error": "Database temporarily unavailable"})
        self.assertTrue(any("database is locked" in message for message in logs.output))

    def test_proxy_decision_requires_active_session(self):
        with patch("backend.routes.proxy.evaluate_http_payload", return_value=_make_result(Decision.ALLOW)):
            response = self.client.post("/api/proxy/decision", json=self._payload())

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "No active proxy session is available"})

    def test_proxy_decision_rejects_invalid_structures_before_evaluation(self):
        invalid_payloads = (
            self._payload(url="/relative"),
            self._payload(url="ftp://example.com/file"),
            self._payload(url="https://user:pass@example.com/"),
            self._payload(method="TRACE"),
            self._payload(headers={"x-count": 1}),
            self._payload(headers={"x-test": "ok\r\nInjected: yes"}),
            self._payload(body={"nested": "object"}),
            self._payload(type="UNKNOWN"),
            self._payload(host="other.example"),
        )

        with patch("backend.routes.proxy.evaluate_http_payload") as evaluate:
            for payload in invalid_payloads:
                with self.subTest(payload=payload):
                    response = self.client.post("/api/proxy/decision", json=payload)
                    self.assertEqual(response.status_code, 400)

        evaluate.assert_not_called()
        self.assertEqual(store.events_list_all({}), [])

    def test_proxy_decision_rejects_oversized_body(self):
        response = self.client.post(
            "/api/proxy/decision",
            json=self._payload(body="x" * (MAX_BODY_BYTES + 1)),
        )

        self.assertEqual(response.status_code, 413)
        self.assertIn("size limit", response.get_json()["error"])

    def test_proxy_decision_rejects_oversized_json_envelope(self):
        response = self.client.post(
            "/api/proxy/decision",
            data=b"{" + b"x" * MAX_PROXY_ENVELOPE_BYTES + b"}",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 413)
        self.assertIn("capacity limit", response.get_json()["error"].lower())

    def test_proxy_payload_accepts_body_at_exact_limit(self):
        payload, error, status = validate_proxy_payload(
            self._payload(body="x" * MAX_BODY_BYTES)
        )

        self.assertIsNone(error)
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["body"]), MAX_BODY_BYTES)

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

    def test_proxy_decision_rejects_closed_session_id(self):
        started = ensure_proxy_session_started(environment="test")
        closed = store.session_try_close(started["session_id"], datetime.now(timezone.utc))
        self.assertEqual(closed, "closed")

        with patch("backend.routes.proxy.evaluate_http_payload", return_value=_make_result(Decision.ALLOW)):
            response = self.client.post(
                "/api/proxy/decision",
                json=self._payload(session_id=started["session_id"]),
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "Provided session_id is already closed"})

    def test_proxy_control_start_creates_session(self):
        with (
            patch("backend.routes.proxy_control.start_proxy_process", return_value=(True, "started")),
            patch("backend.routes.proxy_control.proxy_is_running", return_value=True),
        ):
            response = self.client.post("/api/proxy/control", json={"active": True, "environment": "test"})

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["active"], True)
        self.assertEqual(body["message"], "started")
        self.assertEqual(body["session"]["agent"], "AllTraffic")
        self.assertEqual(body["session"]["environment"], "test")
        self.assertTrue(body["session"]["created"])

        session = store.session_get(body["session"]["session_id"])
        self.assertIsNotNone(session)
        self.assertIsNone(session["end_time"])
        self.assertEqual(session["environment"], "test")

    def test_proxy_control_start_uses_selected_agent(self):
        with (
            patch("backend.routes.proxy_control.start_proxy_process", return_value=(True, "started")) as start_proxy,
            patch("backend.routes.proxy_control.proxy_is_running", return_value=True),
        ):
            response = self.client.post(
                "/api/proxy/control",
                json={
                    "active": True,
                    "environment": "test",
                    "agent_name": "MicrosoftEdge",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["session"]["agent"], "MicrosoftEdge")
        start_proxy.assert_called_once_with(
            agent_name="MicrosoftEdge",
            environment="test",
        )

        session = store.session_get(body["session"]["session_id"])
        self.assertIsNotNone(session)
        self.assertEqual(session["agent_name"], "MicrosoftEdge")

    def test_proxy_decision_persists_contextual_rule_analysis(self):
        """Contextual RuleResults flow through to `rules_analysis` and register
        in `rules` with `rule_type='contextual'` plus the right weight."""
        started = ensure_proxy_session_started(environment="test")

        with patch(
            "backend.routes.proxy.evaluate_http_payload",
            return_value=_make_contextual_result(),
        ):
            response = self.client.post("/api/proxy/decision", json=self._payload())

        self.assertEqual(response.status_code, 200)
        audit = response.get_json()["audit"]
        self.assertEqual(audit["session_id"], started["session_id"])
        self.assertEqual(audit["risk_score"], 0.55)
        self.assertEqual(audit["triggered_rule_count"], 2)

        analyses = store.rule_analysis_list_for_event(audit["event_id"])
        rule_codes = {item["rule_code"] for item in analyses}
        self.assertIn("previously_warned_domain_in_session", rule_codes)
        contextual_row = next(
            item
            for item in analyses
            if item["rule_code"] == "previously_warned_domain_in_session"
        )
        self.assertEqual(contextual_row["rule_score"], 0.4)
        self.assertEqual(contextual_row["hard_block"], 0)
        self.assertIn("evil.com", contextual_row["details"])

        registered = store.rule_get("previously_warned_domain_in_session")
        self.assertIsNotNone(registered)
        self.assertEqual(registered["rule_type"], "contextual")
        self.assertEqual(registered["compute_class"], "cheap")
        self.assertEqual(registered["is_hard_block"], 0)
        self.assertEqual(registered["weight"], 0.20)

    def test_proxy_control_stop_closes_open_session(self):
        started = ensure_proxy_session_started(environment="test")

        with (
            patch("backend.routes.proxy_control.stop_proxy_process", return_value=(True, "stopped")),
            patch("backend.routes.proxy_control.proxy_is_running", return_value=False),
        ):
            response = self.client.post("/api/proxy/control", json={"active": False, "environment": "test"})

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["active"], False)
        self.assertEqual(body["message"], "stopped")
        self.assertTrue(body["session"]["closed"])
        self.assertEqual(body["session"]["session_id"], started["session_id"])

        session = store.session_get(started["session_id"])
        self.assertIsNotNone(session)
        self.assertIsNotNone(session["end_time"])

        log_records = self._audit_log_records()
        self.assertEqual(len(log_records), 2)
        self.assertEqual(log_records[0]["event"], "proxy_session_started")
        closed = log_records[1]
        self.assertEqual(closed["event"], "proxy_session_closed")
        self.assertEqual(closed["reason"], "proxy_stopped")

    def test_proxy_control_stop_addresses_the_named_agent(self):
        """Stop has to name the agent, or it would stop whichever instance the
        launcher happened to reach for."""
        with (
            patch("backend.routes.proxy_control.stop_proxy_process", return_value=(True, "stopped")) as stop_proxy,
            patch("backend.routes.proxy_control.proxy_is_running", return_value=False),
        ):
            response = self.client.post(
                "/api/proxy/control",
                json={"active": False, "environment": "test", "agent_name": "MicrosoftEdge"},
            )

        self.assertEqual(response.status_code, 200)
        stop_proxy.assert_called_once_with(agent_name="MicrosoftEdge")
        self.assertEqual(response.get_json()["agent_name"], "MicrosoftEdge")

    def test_proxy_control_reports_the_endpoint_of_the_agent_it_started(self):
        with (
            patch("backend.routes.proxy_control.start_proxy_process", return_value=(True, "started")),
            patch("backend.routes.proxy_control.proxy_is_running", return_value=True),
        ):
            response = self.client.post(
                "/api/proxy/control",
                json={"active": True, "environment": "test", "agent_name": "MicrosoftEdge"},
            )

        body = response.get_json()
        self.assertEqual(body["proxy_port"], 8082)
        self.assertEqual(body["admin_port"], 8182)

    def test_proxy_control_rejects_an_agent_with_no_allocation(self):
        with (
            patch("backend.routes.proxy_control.start_proxy_process") as start_proxy,
            patch("backend.routes.proxy_control.proxy_is_running", return_value=False),
        ):
            response = self.client.post(
                "/api/proxy/control",
                json={"active": True, "environment": "test", "agent_name": "Firefox"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "Unknown agent: Firefox"})
        start_proxy.assert_not_called()

    def test_proxy_status_reports_one_entry_per_agent(self):
        snapshot = [
            {
                "agent_name": "AllTraffic",
                "active": True,
                "proxy_port": 8080,
                "admin_port": 8180,
                "environment": "prod",
            },
            {
                "agent_name": "BrowserOS",
                "active": False,
                "proxy_port": 8081,
                "admin_port": 8181,
                "environment": None,
            },
            {
                "agent_name": "MicrosoftEdge",
                "active": False,
                "proxy_port": 8082,
                "admin_port": 8182,
                "environment": None,
            },
        ]
        with (
            patch("backend.routes.proxy_control.proxy_status_snapshot", return_value=snapshot),
            patch("backend.routes.proxy_control.any_proxy_running", return_value=True),
        ):
            response = self.client.get("/api/proxy/status")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["active"], True)
        self.assertEqual(body["agents"], snapshot)


class NormalizeProxyAgentNameTestCase(unittest.TestCase):
    def test_legacy_gemini_maps_to_microsoft_edge(self):
        self.assertEqual(normalize_proxy_agent_name("Gemini"), "MicrosoftEdge")

    def test_canonical_names_are_unchanged(self):
        self.assertEqual(normalize_proxy_agent_name("MicrosoftEdge"), "MicrosoftEdge")
        self.assertEqual(normalize_proxy_agent_name("BrowserOS"), "BrowserOS")

    def test_canonical_names_match_case_insensitively(self):
        self.assertEqual(normalize_proxy_agent_name("microsoftedge"), "MicrosoftEdge")
        self.assertEqual(normalize_proxy_agent_name("browseros"), "BrowserOS")

    def test_display_spellings_of_the_catch_all_map_to_its_id(self):
        for spelling in ("All traffic", "all-traffic", "alltraffic"):
            self.assertEqual(normalize_proxy_agent_name(spelling), "AllTraffic")

    def test_default_agent_when_missing(self):
        self.assertEqual(normalize_proxy_agent_name(None), "AllTraffic")
        self.assertEqual(normalize_proxy_agent_name(""), "AllTraffic")


if __name__ == "__main__":
    unittest.main()
