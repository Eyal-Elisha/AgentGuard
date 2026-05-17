from __future__ import annotations

from mitmproxy import http

from backend.analysis.rules import Decision
from backend.custom_blacklist import custom_blacklist_matches
from backend.proxy.enforcement import BackendDecision, build_enforcement_response, local_rule_block_decision
from backend.proxy.filter_logging import should_log_request, should_log_response
from backend.proxy.filter_requests import should_forward
from backend.proxy.request_decision import fetch_backend_decision
from backend.proxy.response_analysis import analyze_response_safe
from backend.proxy.utils import build_request_data, pretty_print, response_data_with_evaluation
from backend.proxy.rule_engine import get_custom_blacklist


def _log_request(flow: http.HTTPFlow, decision) -> None:
    if not should_log_request(flow):
        return

    try:
        data = build_request_data(flow)
        data["enforcement"] = decision.as_log_dict()
        pretty_print(f"{flow.request.method} {flow.request.host}", data)
    except Exception:
        return

def handle_request(flow: http.HTTPFlow) -> None:
    if custom_blacklist_matches(flow.request.host, flow.request.pretty_url, get_custom_blacklist()):
        if not should_forward(flow):
            decision = local_rule_block_decision(
                rule_id="custom_blacklist",
                explanation=f"URL '{flow.request.pretty_url}' matches the custom local blacklist",
                source="proxy_custom_blacklist",
            )
            flow.metadata["agentguard_enforcement"] = decision.as_log_dict()
            flow.response = build_enforcement_response(decision)
            _log_request(flow, decision)
            return

    if not should_forward(flow):
        return

    decision = fetch_backend_decision(flow)
    flow.metadata["agentguard_forwarded_to_backend"] = True
    flow.metadata["agentguard_enforcement"] = decision.as_log_dict()

    if decision.decision == Decision.BLOCK and not decision.passive_mode:
        flow.response = build_enforcement_response(decision)

    _log_request(flow, decision)


def handle_response(flow: http.HTTPFlow) -> None:
    if not (should_forward(flow) and flow.response):
        return
    if not should_log_response(flow):
        return

    result = analyze_response_safe(flow)
    data = response_data_with_evaluation(flow, result)
    pretty_print(f"{flow.response.status_code} {flow.request.host}", data)
