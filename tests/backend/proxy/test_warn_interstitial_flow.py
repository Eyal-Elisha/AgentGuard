from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from backend.analysis.rules import Decision
from backend.proxy.addon import handle_request, handle_response
from backend.proxy.request_decision import BackendDecision
from backend.proxy.warn_bypass import BYPASS_QUERY_PARAM, mint_bypass_token


class FakeQuery:
    """Minimal stand-in for mitmproxy's flow.request.query (MultiDictView)."""

    def __init__(self, items=None):
        self._d = dict(items or {})

    def get(self, key, default=None):
        return self._d.get(key, default)

    def pop(self, key, default=None):
        return self._d.pop(key, default)

    def __contains__(self, key):
        return key in self._d


def _make_get_flow(*, url="https://example.com/login", query_items=None):
    request_obj = SimpleNamespace(
        method="GET",
        host="example.com",
        pretty_url=url,
        headers={"user-agent": "Mozilla/5.0"},
        content=b"",
        query=FakeQuery(query_items or {}),
        get_text=lambda: "",
    )
    return SimpleNamespace(request=request_obj, response=None, metadata={})


def _warn_decision(score=0.45):
    return BackendDecision(
        decision=Decision.WARN,
        reason="warn",
        evaluation={
            "decision": "warn",
            "risk_score": score,
            "rule_results": [
                {
                    "rule_id": "brand_domain_mismatch",
                    "rule_type": "deterministic",
                    "score": 1.0,
                    "hard_block": False,
                    "explanation": "Page references brand on non-official host",
                    "triggered": True,
                },
            ],
        },
        source="backend",
    )


def test_get_warn_returns_interstitial_html():
    flow = _make_get_flow()
    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=_warn_decision()):
        handle_request(flow)

    assert flow.response is not None
    assert flow.response.status_code == 200
    body = flow.response.content.decode("utf-8")
    assert "AgentGuard" in body
    assert "brand_domain_mismatch" in body
    assert BYPASS_QUERY_PARAM in body  # interstitial embeds the bypass link
    assert flow.metadata.get("agentguard_warn_bypassed") is not True


def test_get_warn_with_valid_bypass_token_passes_through():
    token = mint_bypass_token("https://example.com/login")
    flow = _make_get_flow(query_items={BYPASS_QUERY_PARAM: token})

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=_warn_decision()):
        handle_request(flow)

    assert flow.response is None
    assert flow.metadata.get("agentguard_warn_bypassed") is True
    assert BYPASS_QUERY_PARAM not in flow.request.query


def test_unknown_bypass_token_falls_through_to_evaluation():
    flow = _make_get_flow(query_items={BYPASS_QUERY_PARAM: "not-a-real-token"})

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=_warn_decision()):
        handle_request(flow)

    # Token was stale, so the interstitial is rendered as if no token was given.
    assert flow.response is not None
    assert flow.response.status_code == 200
    # The stale param is stripped before the request would have been forwarded.
    assert BYPASS_QUERY_PARAM not in flow.request.query


def test_post_warn_does_not_show_interstitial():
    flow = _make_get_flow()
    flow.request.method = "POST"
    flow.request.content = b"foo=bar"
    flow.request.get_text = lambda: "foo=bar"

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=_warn_decision()):
        handle_request(flow)

    assert flow.response is None  # POST falls through, behaviour unchanged


def test_response_warn_replaces_body_with_interstitial():
    flow = _make_get_flow()
    flow.response = SimpleNamespace(
        status_code=200,
        reason="OK",
        content=b"<html>original</html>",
        headers={"content-type": "text/html", "content-encoding": "gzip", "content-length": "20"},
        get_text=lambda: "<html>original</html>",
    )

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_response", return_value=True
    ), patch(
        "backend.proxy.addon.should_ignore_response", return_value=False
    ), patch(
        "backend.proxy.addon.fetch_backend_response_decision", return_value=_warn_decision()
    ), patch("backend.proxy.addon.pretty_print"):
        handle_response(flow)

    body = flow.response.content.decode("utf-8")
    assert "AgentGuard" in body
    assert "brand_domain_mismatch" in body
    assert flow.response.status_code == 200
    assert "content-encoding" not in flow.response.headers
    assert flow.response.headers.get("Content-Type", "").startswith("text/html")


def test_response_skipped_when_request_was_bypassed():
    flow = _make_get_flow()
    flow.metadata["agentguard_warn_bypassed"] = True
    flow.response = SimpleNamespace(
        status_code=200,
        reason="OK",
        content=b"<html>real page</html>",
        headers={"content-type": "text/html"},
        get_text=lambda: "<html>real page</html>",
    )

    # If `fetch_backend_response_decision` is called it would surface here.
    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_response", return_value=True
    ), patch(
        "backend.proxy.addon.should_ignore_response", return_value=False
    ), patch(
        "backend.proxy.addon.fetch_backend_response_decision",
        side_effect=AssertionError("response evaluation must be skipped after bypass"),
    ), patch("backend.proxy.addon.pretty_print"):
        handle_response(flow)

    assert flow.response.content == b"<html>real page</html>"
