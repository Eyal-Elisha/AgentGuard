from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

from backend.analysis.rules import Decision
from backend.proxy.request_decision import BackendDecision
from backend.proxy.addon import handle_request


class _FakeQuery:
    def __init__(self, items=None):
        self._d = dict(items or {})

    def get(self, key, default=None):
        return self._d.get(key, default)

    def pop(self, key, default=None):
        return self._d.pop(key, default)


def _make_flow():
    request_obj = SimpleNamespace(
        method="POST",
        host="example.com",
        pretty_url="https://example.com/login",
        headers={"user-agent": "Mozilla/5.0"},
        content=b"username=a&password=b",
        query=_FakeQuery(),
        get_text=lambda: "username=a&password=b",
    )
    return SimpleNamespace(request=request_obj, response=None, metadata={})


def test_request_blocks_before_upstream_when_backend_blocks():
    flow = _make_flow()
    decision = BackendDecision(
        decision=Decision.BLOCK,
        reason="blocked upstream",
        evaluation={"decision": "block"},
        source="backend",
    )

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=decision):
        handle_request(flow)

    assert flow.response is not None
    assert flow.response.status_code == 403
    assert flow.metadata["agentguard_enforcement"]["decision"] == "block"


def test_request_continues_when_backend_warns():
    flow = _make_flow()
    decision = BackendDecision(
        decision=Decision.WARN,
        reason="warn only",
        evaluation={"decision": "warn"},
        source="backend",
    )

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=decision):
        handle_request(flow)

    assert flow.response is None
    assert flow.metadata["agentguard_enforcement"]["decision"] == "warn"


def test_request_still_blocks_when_logging_fails():
    flow = _make_flow()
    decision = BackendDecision(
        decision=Decision.BLOCK,
        reason="blocked upstream",
        evaluation={"decision": "block"},
        source="backend",
    )

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=True
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=decision), patch(
        "backend.proxy.addon.pretty_print", side_effect=UnicodeEncodeError("charmap", "🔏", 0, 1, "bad")
    ):
        handle_request(flow)

    assert flow.response is not None
    assert flow.response.status_code == 403


def test_blacklisted_subresource_is_blocked_locally_without_backend_call():
    flow = _make_flow()
    flow.request.method = "GET"
    flow.request.host = "blocked.example.test"
    flow.request.pretty_url = "https://blocked.example.test/favicon.ico"
    flow.request.headers = {
        "user-agent": "Mozilla/5.0 Chrome/120.0.0.0 Electron/30.0.0.0",
        "accept": "image/avif,image/webp,*/*",
        "sec-fetch-dest": "image",
        "sec-fetch-mode": "no-cors",
    }
    flow.request.content = b""
    flow.request.get_text = lambda: ""

    with patch("backend.proxy.addon.custom_blacklist_matches", return_value=True), patch(
        "backend.proxy.addon.fetch_backend_decision"
    ) as fetch_backend_decision:
        handle_request(flow)

    fetch_backend_decision.assert_not_called()
    assert flow.response is not None
    assert flow.response.status_code == 403
    assert flow.metadata["agentguard_enforcement"]["source"] == "proxy_custom_blacklist"


def test_browseros_block_gets_soft_block_json_with_alternatives():
    flow = _make_flow()
    flow.request.headers["x-agentguard-agent"] = "browserOS"
    decision = BackendDecision(
        decision=Decision.BLOCK,
        reason="blocked upstream",
        evaluation={"decision": "block", "risk_score": 0.91, "hard_block_triggered": True},
        source="backend",
    )

    with patch("backend.proxy.addon.should_forward", return_value=True), patch(
        "backend.proxy.addon.should_log_request", return_value=False
    ), patch("backend.proxy.addon.fetch_backend_decision", return_value=decision):
        handle_request(flow)

    assert flow.response is not None
    assert flow.response.status_code == 403
    assert flow.response.headers["Content-Type"].startswith("application/json")
    assert flow.response.headers["X-AgentGuard-Decision"] == "block"
    assert flow.response.headers["X-AgentGuard-Continuation"] == "available"
    payload = json.loads(flow.response.content.decode("utf-8"))
    assert payload["enforcement_mode"] == "soft_block"
    assert payload["retryable"] is True
    assert payload["safe_alternatives"][0]["type"] == "search"
