from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend import create_app
from backend.analysis.rules import Decision, EvaluationResult


@pytest.fixture
def proxy_test_client():
    """create_app() requires JWT and a database URL; isolate env for proxy route tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_url_path = Path(temp_dir, "test.db").resolve().as_posix()
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET": "test-jwt-secret-proxy-routes",
                "DATABASE_URL": f"sqlite:///{db_url_path}",
            },
            clear=False,
        ):
            yield create_app().test_client()


def _make_result(decision: Decision) -> EvaluationResult:
    return EvaluationResult(
        decision=decision,
        risk_score=0.42 if decision == Decision.WARN else 0.0,
        rule_results=[],
        hard_block_triggered=decision == Decision.BLOCK,
        stage_b_required=decision == Decision.WARN,
    )


def test_proxy_decision_route_returns_backend_decision(proxy_test_client):
    with patch("backend.routes.proxy.evaluate_http_payload", return_value=_make_result(Decision.WARN)):
        response = proxy_test_client.post(
            "/api/proxy/decision",
            json={
                "url": "https://example.com/login",
                "method": "POST",
                "headers": {"content-type": "application/x-www-form-urlencoded"},
                "body": "username=a&password=b",
            },
        )

    assert response.status_code == 200
    assert response.json["decision"] == "warn"
    assert response.json["evaluation"]["decision"] == "warn"


def test_proxy_decision_route_rejects_missing_fields(proxy_test_client):
    response = proxy_test_client.post(
        "/api/proxy/decision",
        json={
            "url": "https://example.com/login",
            "method": "POST",
        },
    )

    assert response.status_code == 400
    assert "Missing required fields" in response.json["error"]


def test_proxy_decision_route_rejects_non_object_headers(proxy_test_client):
    response = proxy_test_client.post(
        "/api/proxy/decision",
        json={
            "url": "https://example.com/login",
            "method": "POST",
            "headers": ["not", "a", "dict"],
            "body": "",
        },
    )

    assert response.status_code == 400
    assert "'headers' must be an object" == response.json["error"]


def test_proxy_decision_route_rejects_blank_url(proxy_test_client):
    response = proxy_test_client.post(
        "/api/proxy/decision",
        json={
            "url": "   ",
            "method": "POST",
            "headers": {},
            "body": "",
        },
    )

    assert response.status_code == 400
    assert "'url' must be a non-empty string" == response.json["error"]


def test_proxy_decision_route_normalizes_method_and_headers(proxy_test_client):
    with patch("backend.routes.proxy.evaluate_http_payload", return_value=_make_result(Decision.ALLOW)) as mocked:
        response = proxy_test_client.post(
            "/api/proxy/decision",
            json={
                "url": "https://example.com/login",
                "method": "post",
                "headers": {"x-retry-count": 1},
                "body": None,
            },
        )

    assert response.status_code == 200
    mocked.assert_called_once_with(
        url="https://example.com/login",
        method="POST",
        headers={"x-retry-count": "1"},
        body=b"",
    )


def test_proxy_decision_route_rejects_non_local_requests(proxy_test_client):
    response = proxy_test_client.post(
        "/api/proxy/decision",
        json={
            "url": "https://example.com/login",
            "method": "POST",
            "headers": {},
            "body": "",
        },
        environ_overrides={"REMOTE_ADDR": "203.0.113.25"},
    )

    assert response.status_code == 403
    assert "localhost" in response.json["error"]
