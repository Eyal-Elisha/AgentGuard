from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from backend.analysis.rules import Decision
from backend.proxy.request_decision import BackendDecision
from backend.proxy.addon import handle_request


def _make_flow():
    request_obj = SimpleNamespace(
        method="POST",
        host="example.com",
        pretty_url="https://example.com/login",
        headers={"user-agent": "Mozilla/5.0"},
        content=b"username=a&password=b",
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
