from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from backend.analysis.rules import Decision
from backend.proxy.addon import handle_request, handle_response
from backend.proxy.enforcement import BackendDecision
from backend.proxy.warn_bypass import (
    BYPASS_QUERY_PARAM,
    clear_continue_anyway_for_host,
    mint_bypass_token,
    open_subresource_window,
)


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


def _make_get_flow(*, url="https://example.com/login", query_items=None, headers=None):
    if query_items:
        from urllib.parse import urlencode, urlsplit, urlunsplit

        parts = urlsplit(url)
        url = urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query_items),
            parts.fragment,
        ))

    hdrs = dict(headers) if headers else {}
    if "user-agent" not in {k.lower() for k in hdrs}:
        hdrs["user-agent"] = "Mozilla/5.0"

    request_obj = SimpleNamespace(
        method="GET",
        host="example.com",
        pretty_url=url,
        headers=hdrs,
        content=b"",
        query=FakeQuery(query_items or {}),
        get_text=lambda: "",
    )
    return SimpleNamespace(request=request_obj, response=None, metadata={})


def _warn_decision(score=0.45, passive_mode=False):
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
        passive_mode=passive_mode,
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
    # The interstitial's "Continue anyway" link carries the bypass token.
    assert BYPASS_QUERY_PARAM in body
    assert flow.metadata.get("agentguard_suppressed_warn_ui") is not True


def test_bypass_token_in_url_redirects_to_clean_url_and_registers_continue():
    """When the proxy sees `?_agentguard_bypass=<token>`, it must:
       1. validate + consume the token,
       2. register continue-anyway state for this host + clean URL,
       3. respond with 302 to the same URL with the token stripped."""
    clear_continue_anyway_for_host("example.com")
    token = mint_bypass_token("example.com")

    flow = _make_get_flow(
        url="https://example.com/login",
        query_items={BYPASS_QUERY_PARAM: token},
    )

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.fetch_backend_decision",
        side_effect=AssertionError("backend must not be called during token redemption"),
    ):
        handle_request(flow)

    assert flow.response is not None
    assert flow.response.status_code == 302
    location = flow.response.headers.get("Location", "")
    assert BYPASS_QUERY_PARAM not in location
    assert "example.com/login" in location

    # Short subresource window so assets can load without interstitial loops.
    from backend.proxy.warn_bypass import subresource_window_active

    assert subresource_window_active("example.com") is True


def test_bypass_token_registers_normalized_destination_url_for_continue():
    """Regression: clean_url must be computed before register_continue_anyway."""
    clear_continue_anyway_for_host("example.com")
    token = mint_bypass_token("example.com")
    seen = []

    def _record(host: str, clean: str) -> None:
        seen.append((host, clean))

    flow = _make_get_flow(
        url="https://example.com/login?x=1",
        query_items={BYPASS_QUERY_PARAM: token},
    )

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.fetch_backend_decision",
        side_effect=AssertionError("backend must not be called during token redemption"),
    ), patch("backend.proxy.addon.register_continue_anyway", side_effect=_record):
        handle_request(flow)

    assert seen == [("example.com", "https://example.com/login?x=1")]


def test_continue_anyway_suppresses_document_once_but_still_calls_backend():
    """After register_continue_anyway, the matching main-document GET must still
    hit the backend while skipping the interstitial; a different path must warn."""
    clear_continue_anyway_for_host("example.com")
    from backend.proxy.warn_bypass import register_continue_anyway

    register_continue_anyway("example.com", "https://example.com/login")

    flow = _make_get_flow(url="https://example.com/login")
    calls = {"n": 0}

    def _decision():
        calls["n"] += 1
        return _warn_decision()

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", side_effect=_decision):
        handle_request(flow)

    assert calls["n"] == 1
    assert flow.response is None
    assert flow.metadata.get("agentguard_suppressed_warn_ui") is True

    flow2 = _make_get_flow(url="https://example.com/other")
    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=_warn_decision()):
        handle_request(flow2)

    assert flow2.response is not None
    assert flow2.response.status_code == 200
    assert "AgentGuard" in flow2.response.content.decode("utf-8")


def test_continue_anyway_suppresses_subresource_get_during_window():
    clear_continue_anyway_for_host("example.com")
    open_subresource_window("example.com")

    flow = _make_get_flow(
        url="https://example.com/assets/app.js",
        headers={
            "user-agent": "Mozilla/5.0",
            "sec-fetch-dest": "script",
            "sec-fetch-mode": "no-cors",
        },
    )
    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=_warn_decision()):
        handle_request(flow)

    assert flow.response is None
    assert flow.metadata.get("agentguard_suppressed_warn_ui") is True


def test_clean_pass_is_scoped_to_one_host():
    """A clean-pass for host A must not bypass requests to host B."""
    clear_continue_anyway_for_host("example.com")
    clear_continue_anyway_for_host("attacker.example")
    open_subresource_window("example.com")

    flow = _make_get_flow(url="https://attacker.example/")
    flow.request.host = "attacker.example"

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=_warn_decision()):
        handle_request(flow)

    # No clean-pass for attacker.example → normal evaluation → warn.
    assert flow.response is not None
    assert flow.response.status_code == 200


def test_stale_bypass_token_in_url_is_stripped_and_falls_through():
    clear_continue_anyway_for_host("example.com")
    flow = _make_get_flow(query_items={BYPASS_QUERY_PARAM: "not-a-real-token"})

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=_warn_decision()):
        handle_request(flow)

    # Stale token → fresh interstitial.
    assert flow.response is not None
    assert flow.response.status_code == 200
    # Stale param is stripped so the origin never sees it.
    assert BYPASS_QUERY_PARAM not in flow.request.query


def test_post_warn_does_not_show_interstitial():
    clear_continue_anyway_for_host("example.com")
    flow = _make_get_flow()
    flow.request.method = "POST"
    flow.request.content = b"foo=bar"
    flow.request.get_text = lambda: "foo=bar"

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=_warn_decision()):
        handle_request(flow)

    assert flow.response is None  # POST falls through, behaviour unchanged


def test_passive_mode_suppresses_warn_interstitial():
    """When the backend is in passive mode, WARN must NOT render the interstitial."""
    clear_continue_anyway_for_host("example.com")
    flow = _make_get_flow()
    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch(
        "backend.proxy.addon.fetch_backend_decision",
        return_value=_warn_decision(passive_mode=True),
    ):
        handle_request(flow)

    assert flow.response is None


def test_response_warn_replaces_body_with_interstitial():
    clear_continue_anyway_for_host("example.com")
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


def test_response_passive_mode_does_not_replace_body():
    """Passive mode must leave the real response body alone, even on WARN."""
    clear_continue_anyway_for_host("example.com")
    flow = _make_get_flow()
    original_body = b"<html>real page</html>"
    flow.response = SimpleNamespace(
        status_code=200,
        reason="OK",
        content=original_body,
        headers={"content-type": "text/html"},
        get_text=lambda: "<html>real page</html>",
    )

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_response", return_value=True
    ), patch(
        "backend.proxy.addon.should_ignore_response", return_value=False
    ), patch(
        "backend.proxy.addon.fetch_backend_response_decision",
        return_value=_warn_decision(passive_mode=True),
    ), patch("backend.proxy.addon.pretty_print"):
        handle_response(flow)

    assert flow.response.content == original_body


def test_response_suppressed_warn_keeps_body_and_evaluates():
    flow = _make_get_flow()
    flow.metadata["agentguard_suppressed_warn_ui"] = True
    flow.response = SimpleNamespace(
        status_code=200,
        reason="OK",
        content=b"<html>real page</html>",
        headers={"content-type": "text/html"},
        get_text=lambda: "<html>real page</html>",
    )

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_response", return_value=True
    ), patch(
        "backend.proxy.addon.should_ignore_response", return_value=False
    ), patch(
        "backend.proxy.addon.fetch_backend_response_decision",
        return_value=_warn_decision(),
    ), patch("backend.proxy.addon.pretty_print"):
        handle_response(flow)

    assert flow.response.content == b"<html>real page</html>"
    assert isinstance(flow.metadata.get("agentguard_response_evaluation"), dict)
