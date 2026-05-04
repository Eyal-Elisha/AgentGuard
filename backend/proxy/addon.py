from __future__ import annotations

from mitmproxy import http

from backend.analysis.rules import Decision
from backend.proxy.filter_logging import should_log_request, should_log_response
from backend.proxy.filter_requests import should_forward
from backend.proxy.request_decision import build_enforcement_response, fetch_backend_decision
from backend.proxy.response_analysis import analyze_response_safe
from backend.proxy.utils import build_request_data, pretty_print, response_data_with_evaluation


def handle_request(flow: http.HTTPFlow) -> None:
    if not should_forward(flow):
        return

    decision = fetch_backend_decision(flow)
    flow.metadata["agentguard_forwarded_to_backend"] = True
    flow.metadata["agentguard_enforcement"] = decision.as_log_dict()

    if should_log_request(flow):
        data = build_request_data(flow)
        data["enforcement"] = decision.as_log_dict()
        pretty_print(f"{flow.request.method} {flow.request.host}", data)

    if decision.decision == Decision.BLOCK and not decision.passive_mode:
        flow.response = build_enforcement_response(decision)


def handle_response(flow: http.HTTPFlow) -> None:
    if not (should_forward(flow) and flow.response):
        return
    if not should_log_response(flow):
        return

    result = analyze_response_safe(flow)
    data = response_data_with_evaluation(flow, result)
    pretty_print(f"{flow.response.status_code} {flow.request.host}", data)
