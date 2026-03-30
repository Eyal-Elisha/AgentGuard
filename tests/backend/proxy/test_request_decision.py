from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

from backend.analysis.rules import Decision
from backend.proxy.request_decision import (
    BackendDecision,
    build_enforcement_response,
    fetch_backend_decision,
)


def _make_flow():
    request = SimpleNamespace(
        method="POST",
        pretty_url="https://example.com/login",
        host="example.com",
        headers={"content-type": "application/x-www-form-urlencoded"},
        content=b"username=a&password=b",
        get_text=lambda: "username=a&password=b",
    )
    return SimpleNamespace(request=request, metadata={})


def _settings_env(**overrides):
    values = {
        "API_PORT": "3000",
        "AGENTGUARD_BACKEND_TIMEOUT_SECONDS": "10",
        "AGENTGUARD_BACKEND_FAILURE_MODE": "fail_closed",
    }
    values.update(overrides)
    return patch.dict(os.environ, values, clear=False)


def test_fetch_backend_decision_blocks_on_timeout():
    with _settings_env(), patch("backend.proxy.decision_client.requests.Session") as session_cls:
        session = Mock()
        session.post.side_effect = requests.Timeout()
        session_cls.return_value = session

        decision = fetch_backend_decision(_make_flow())

    assert decision.decision == Decision.BLOCK
    assert decision.source == "backend_timeout"
    assert "decision service is unavailable" in decision.reason.lower()


def test_fetch_backend_decision_allows_on_timeout_when_fail_open():
    with _settings_env(AGENTGUARD_BACKEND_FAILURE_MODE="fail_open"):
        with patch("backend.proxy.decision_client.requests.Session") as session_cls:
            session = Mock()
            session.post.side_effect = requests.Timeout()
            session_cls.return_value = session

            decision = fetch_backend_decision(_make_flow())

    assert decision.decision == Decision.ALLOW
    assert decision.source == "backend_timeout"
    assert "fail-open mode is enabled" in decision.reason.lower()


def test_fetch_backend_decision_returns_backend_allow():
    with _settings_env(), patch("backend.proxy.decision_client.requests.Session") as session_cls:
        response = Mock()
        response.json.return_value = {
            "decision": "allow",
            "evaluation": {"decision": "allow", "risk_score": 0.0},
        }
        response.raise_for_status.return_value = None

        session = Mock()
        session.post.return_value = response
        session_cls.return_value = session

        decision = fetch_backend_decision(_make_flow())

    assert decision.decision == Decision.ALLOW
    assert decision.source == "backend"
    assert decision.evaluation == {"decision": "allow", "risk_score": 0.0}


def test_fetch_backend_decision_block_reason_includes_hard_block_explanation():
    with _settings_env(), patch("backend.proxy.decision_client.requests.Session") as session_cls:
        response = Mock()
        response.json.return_value = {
            "decision": "block",
            "evaluation": {
                "decision": "block",
                "hard_block_triggered": True,
                "rule_results": [
                    {
                        "rule_id": "unencrypted_connection",
                        "triggered": True,
                        "hard_block": True,
                        "explanation": "Connection is unencrypted ('http://')",
                    },
                ],
            },
        }
        response.raise_for_status.return_value = None

        session = Mock()
        session.post.return_value = response
        session_cls.return_value = session

        decision = fetch_backend_decision(_make_flow())

    assert decision.decision == Decision.BLOCK
    assert "Reason:" in decision.reason
    assert "Connection is unencrypted ('http://')" in decision.reason


def test_fetch_backend_decision_block_reason_summarizes_score_based_block():
    with _settings_env(), patch("backend.proxy.decision_client.requests.Session") as session_cls:
        response = Mock()
        response.json.return_value = {
            "decision": "block",
            "evaluation": {
                "decision": "block",
                "hard_block_triggered": False,
                "rule_results": [
                    {
                        "rule_id": "sensitive_fields",
                        "triggered": True,
                        "hard_block": False,
                        "explanation": "Page contains input fields associated with credential or secret collection",
                    },
                ],
            },
        }
        response.raise_for_status.return_value = None

        session = Mock()
        session.post.return_value = response
        session_cls.return_value = session

        decision = fetch_backend_decision(_make_flow())

    assert decision.decision == Decision.BLOCK
    assert "credential or secret collection" in decision.reason


def test_fetch_backend_decision_blocks_on_invalid_payload_by_default():
    with _settings_env(), patch("backend.proxy.decision_client.requests.Session") as session_cls:
        response = Mock()
        response.json.return_value = ["not", "an", "object"]
        response.raise_for_status.return_value = None

        session = Mock()
        session.post.return_value = response
        session_cls.return_value = session

        decision = fetch_backend_decision(_make_flow())

    assert decision.decision == Decision.BLOCK
    assert decision.source == "backend_error"
    assert "invalid response" in decision.reason.lower()


def test_fetch_backend_decision_allows_invalid_payload_when_fail_open():
    with _settings_env(AGENTGUARD_BACKEND_FAILURE_MODE="fail_open"):
        with patch("backend.proxy.decision_client.requests.Session") as session_cls:
            response = Mock()
            response.json.return_value = {"decision": "maybe"}
            response.raise_for_status.return_value = None

            session = Mock()
            session.post.return_value = response
            session_cls.return_value = session

            decision = fetch_backend_decision(_make_flow())

    assert decision.decision == Decision.ALLOW
    assert decision.source == "backend_error"
    assert "fail-open mode is enabled" in decision.reason.lower()


def test_fetch_backend_decision_blocks_on_http_error_by_default():
    with _settings_env(), patch("backend.proxy.decision_client.requests.Session") as session_cls:
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("503 Server Error")

        session = Mock()
        session.post.return_value = response
        session_cls.return_value = session

        decision = fetch_backend_decision(_make_flow())

    assert decision.decision == Decision.BLOCK
    assert decision.source == "backend_unreachable"
    assert "decision service is unavailable" in decision.reason.lower()


def test_fetch_backend_decision_uses_default_timeout_when_env_is_invalid():
    with _settings_env(AGENTGUARD_BACKEND_TIMEOUT_SECONDS="abc"):
        with patch("backend.proxy.decision_client.requests.Session") as session_cls:
            response = Mock()
            response.json.return_value = {
                "decision": "allow",
                "evaluation": {"decision": "allow", "risk_score": 0.0},
            }
            response.raise_for_status.return_value = None

            session = Mock()
            session.post.return_value = response
            session_cls.return_value = session

            fetch_backend_decision(_make_flow())

    session.post.assert_called_once()
    assert session.post.call_args.kwargs["timeout"] == 10.0


def test_fetch_backend_decision_uses_api_port_for_local_backend_url():
    with _settings_env(API_PORT="3000"):
        with patch("backend.proxy.decision_client.requests.Session") as session_cls:
            response = Mock()
            response.json.return_value = {
                "decision": "allow",
                "evaluation": {"decision": "allow", "risk_score": 0.0},
            }
            response.raise_for_status.return_value = None

            session = Mock()
            session.post.return_value = response
            session_cls.return_value = session

            fetch_backend_decision(_make_flow())

    session.post.assert_called_once()
    assert session.post.call_args.args[0] == "http://127.0.0.1:3000/api/proxy/decision"


def test_fetch_backend_decision_falls_back_to_default_api_port_when_invalid():
    with _settings_env(API_PORT="oops"):
        with patch("backend.proxy.decision_client.requests.Session") as session_cls:
            response = Mock()
            response.json.return_value = {
                "decision": "allow",
                "evaluation": {"decision": "allow", "risk_score": 0.0},
            }
            response.raise_for_status.return_value = None

            session = Mock()
            session.post.return_value = response
            session_cls.return_value = session

            fetch_backend_decision(_make_flow())

    session.post.assert_called_once()
    assert session.post.call_args.args[0] == "http://127.0.0.1:3000/api/proxy/decision"


def test_build_enforcement_response_uses_fail_closed_status_for_backend_failure():
    decision = BackendDecision(
        decision=Decision.BLOCK,
        reason="backend unavailable",
        evaluation=None,
        source="backend_unreachable",
    )

    response = build_enforcement_response(decision)

    assert response.status_code == 503
    assert response.headers["X-AgentGuard-Decision"] == "block"
