from __future__ import annotations

from mitmproxy import http

from backend.analysis.rules import Decision
from backend.proxy.enforcement import build_warn_body, build_warn_response
from backend.proxy.filter_logging import should_log_request, should_log_response
from backend.proxy.filter_requests import should_forward
from backend.proxy.filters.response_eligibility_filter import should_ignore_response
from backend.proxy.request_decision import build_enforcement_response, fetch_backend_decision
from backend.proxy.response_decision import fetch_backend_response_decision
from backend.proxy.utils import build_request_data, build_response_payload, pretty_print
from backend.proxy.warn_bypass import BYPASS_QUERY_PARAM, consume_bypass_token


def _consume_bypass(flow: http.HTTPFlow) -> bool:
    """If the request carries a valid one-shot bypass token, strip it and
    return True so the proxy lets this single request through unchallenged."""
    token = flow.request.query.get(BYPASS_QUERY_PARAM)
    if not token:
        return False
    matched_url = consume_bypass_token(token)
    if matched_url is None:
        # Stale or unknown token — strip it so it never reaches the origin
        # and let the normal evaluation path run.
        flow.request.query.pop(BYPASS_QUERY_PARAM, None)
        return False
    flow.request.query.pop(BYPASS_QUERY_PARAM, None)
    flow.metadata["agentguard_warn_bypassed"] = True
    return True


def _is_get_navigation(flow: http.HTTPFlow) -> bool:
    """Warn interstitial only makes sense for navigations the browser can render."""
    return flow.request.method.upper() == "GET"


def handle_request(flow: http.HTTPFlow) -> None:
    if not should_forward(flow):
        return

    bypassed = _consume_bypass(flow)

    decision = fetch_backend_decision(flow)
    flow.metadata["agentguard_forwarded_to_backend"] = True
    flow.metadata["agentguard_enforcement"] = decision.as_log_dict()

    if should_log_request(flow):
        data = build_request_data(flow)
        data["enforcement"] = decision.as_log_dict()
        if bypassed:
            data["bypassed"] = True
        pretty_print(f"{flow.request.method} {flow.request.host}", data)

    if decision.decision == Decision.BLOCK and not decision.passive_mode:
        flow.response = build_enforcement_response(decision)
        return

    if (
        decision.decision == Decision.WARN
        and not decision.passive_mode
        and not bypassed
        and _is_get_navigation(flow)
    ):
        flow.response = build_warn_response(
            original_url=flow.request.pretty_url,
            decision=decision,
        )


def handle_response(flow: http.HTTPFlow) -> None:
    if not (should_forward(flow) and flow.response):
        return
    if not should_log_response(flow):
        return

    if should_ignore_response(flow):
        return

    if flow.metadata.get("agentguard_warn_bypassed"):
        # User just clicked "Continue anyway" — let the response through and
        # skip running the response-time evaluation, otherwise the same Warn
        # would re-fire and replace the page with another interstitial.
        return

    decision = fetch_backend_response_decision(flow)
    flow.metadata["agentguard_response_evaluation"] = decision.as_log_dict()

    data = build_response_payload(flow)
    data["evaluation"] = decision.as_log_dict()
    pretty_print(f"{flow.response.status_code} {flow.request.host}", data)

    if (
        decision.decision == Decision.WARN
        and not decision.passive_mode
        and _is_get_navigation(flow)
    ):
        body, headers = build_warn_body(
            original_url=flow.request.pretty_url,
            decision=decision,
        )
        flow.response.status_code = 200
        flow.response.reason = "OK"
        flow.response.content = body
        # Drop encoding so the browser does not try to gunzip our plain HTML;
        # mitmproxy automatically refreshes Content-Length when content is set.
        flow.response.headers.pop("content-encoding", None)
        flow.response.headers.pop("content-length", None)
        for key, value in headers.items():
            flow.response.headers[key] = value
