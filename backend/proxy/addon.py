"""What AgentGuard does to each intercepted flow.

`handle_request` runs before the request reaches the origin, in this order:

  1. a custom-blacklist hit too low-signal to audit is blocked here and now
  2. anything the filter chain rejects is left alone entirely
  3. outbound LLM prompts get the fallback instruction appended
  4. a valid bypass token redirects to the clean URL and returns
  5. the backend decides, and Block or Warn is enforced

`handle_response` re-evaluates once the origin has answered, which is how a
page whose risk is only visible in its HTML still gets caught. By then the
request is already out, so the only enforcement left is rewriting the body.
"""

from __future__ import annotations

from mitmproxy import http

from backend.analysis.rules import Decision
from backend.custom_blacklist import custom_blacklist_matches
from backend.proxy.diagnostics import ADDON_VERSION, diag
from backend.proxy.enforcement import (
    BACKEND_FAILURE_SOURCES,
    block_response_for,
    build_warn_body,
    build_warn_response,
    is_get_navigation,
    local_rule_block_decision,
)
from backend.proxy.filter_logging import should_log_request, should_log_response
from backend.proxy.filter_requests import should_forward
from backend.proxy.filters.response_eligibility_filter import should_ignore_response
from backend.proxy.prompting import augment_request_body
from backend.proxy.request_decision import fetch_backend_decision
from backend.proxy.response_decision import fetch_backend_response_decision
from backend.proxy.rule_engine import get_custom_blacklist
from backend.proxy.utils import build_request_data, build_response_payload, pretty_print
from backend.proxy.warn_bypass import (
    BYPASS_QUERY_PARAM,
    consume_bypass_token,
    register_continue_anyway,
    should_suppress_warn_interstitial,
    strip_query_param,
)

diag(f"loaded {ADDON_VERSION}")

# Last passive-mode value seen from a healthy backend response. Used as the
# fallback while the backend is unreachable, so a session the user put in
# passive mode does not start hard-blocking the moment the backend goes away.
_cached_passive_mode: bool = False


def handle_request(flow: http.HTTPFlow) -> None:
    global _cached_passive_mode

    if _block_low_signal_blacklist_hit(flow):
        return

    if not should_forward(flow):
        return

    augment_request_body(flow.request)

    if _redeem_bypass_token(flow):
        return

    decision = fetch_backend_decision(flow)

    if decision.source == "backend":
        _cached_passive_mode = decision.passive_mode
    elif decision.source in BACKEND_FAILURE_SOURCES and _cached_passive_mode:
        # Backend is down and this session was passive — pass through silently
        # rather than applying the fail-closed default.
        return

    flow.metadata["agentguard_forwarded_to_backend"] = True
    flow.metadata["agentguard_enforcement"] = decision.as_log_dict()
    _log_request(flow, decision)

    if decision.passive_mode:
        return

    if decision.decision == Decision.BLOCK:
        flow.response = block_response_for(flow, decision)
        return

    if decision.decision == Decision.WARN and is_get_navigation(flow):
        _serve_warn_interstitial(flow, decision)


def handle_response(flow: http.HTTPFlow) -> None:
    if not (should_forward(flow) and flow.response):
        return
    if not should_log_response(flow):
        return
    if should_ignore_response(flow):
        return

    decision = fetch_backend_response_decision(flow)
    flow.metadata["agentguard_response_evaluation"] = decision.as_log_dict()

    data = build_response_payload(flow)
    data["evaluation"] = decision.as_log_dict()
    pretty_print(f"{flow.response.status_code} {flow.request.host}", data)

    if decision.decision != Decision.WARN or decision.passive_mode:
        return
    if not is_get_navigation(flow):
        return
    if flow.metadata.get("agentguard_suppressed_warn_ui") or should_suppress_warn_interstitial(flow):
        diag(
            f"WARN at response-time for {flow.request.host} but interstitial "
            f"suppressed - leaving origin body intact"
        )
        return

    diag(
        f"served WARN at response-time for {flow.request.host} "
        f"(replacing body of {flow.response.status_code} response)"
    )
    _replace_body_with_warn(flow, decision)


def _block_low_signal_blacklist_hit(flow: http.HTTPFlow) -> bool:
    """Block a blacklisted URL the filter chain would otherwise drop.

    `should_forward` deliberately declines to audit low-signal blacklist hits
    (a sub-resource, a background request). Without this the user would get no
    enforcement at all on them, so the block is decided here without involving
    the backend.
    """
    if not custom_blacklist_matches(
        flow.request.host, flow.request.pretty_url, get_custom_blacklist()
    ):
        return False
    if should_forward(flow):
        return False

    decision = local_rule_block_decision(
        rule_id="custom_blacklist",
        explanation=f"URL '{flow.request.pretty_url}' matches the custom local blacklist",
        source="proxy_custom_blacklist",
    )
    flow.metadata["agentguard_enforcement"] = decision.as_log_dict()
    flow.response = block_response_for(flow, decision)
    _log_request(flow, decision)
    return True


def _redeem_bypass_token(flow: http.HTTPFlow) -> bool:
    """Honour a `?_agentguard_bypass=<token>` on its way through.

    A token valid for this host registers a continue profile and redirects to
    the same URL without it, so the address bar never keeps the token and the
    page does not bounce back into the interstitial. The backend still sees
    every subsequent request; only the warning UI is suppressed.

    Returns True when the flow has been answered and nothing else should run.
    """
    token = flow.request.query.get(BYPASS_QUERY_PARAM) if BYPASS_QUERY_PARAM in flow.request.query else None
    if not token:
        return False

    matched_host = consume_bypass_token(token)
    if matched_host is None:
        diag(
            f"bypass token in URL for {flow.request.host} is stale/unknown - "
            f"stripping and falling through to normal evaluation"
        )
        flow.request.query.pop(BYPASS_QUERY_PARAM, None)
        return False

    if matched_host.lower() != (flow.request.host or "").lower():
        diag(
            f"bypass token host mismatch (minted for {matched_host}, "
            f"request to {flow.request.host}) - refusing"
        )
        flow.request.query.pop(BYPASS_QUERY_PARAM, None)
        return False

    clean_url = strip_query_param(flow.request.pretty_url, BYPASS_QUERY_PARAM)
    register_continue_anyway(flow.request.host, clean_url)
    diag(f"bypass token redeemed for {flow.request.host} -> 302 to {clean_url}")
    flow.response = http.Response.make(
        302,
        b"",
        {
            "Location": clean_url,
            "Cache-Control": "no-store",
            "X-AgentGuard-Decision": "warn-bypass",
        },
    )
    return True


def _serve_warn_interstitial(flow: http.HTTPFlow, decision) -> None:
    if should_suppress_warn_interstitial(flow):
        flow.metadata["agentguard_suppressed_warn_ui"] = True
        diag(
            f"WARN for {flow.request.host} but interstitial suppressed "
            f"(continue anyway profile) - forwarding to origin"
        )
        return
    flow.response = build_warn_response(
        original_url=flow.request.pretty_url,
        host=flow.request.host,
        decision=decision,
    )
    diag(f"served WARN interstitial for {flow.request.host}")


def _replace_body_with_warn(flow: http.HTTPFlow, decision) -> None:
    body, headers = build_warn_body(
        original_url=flow.request.pretty_url,
        host=flow.request.host,
        decision=decision,
    )
    flow.response.status_code = 200
    flow.response.reason = "OK"
    flow.response.content = body
    # Drop the encoding headers so the browser does not try to gunzip plain
    # HTML; mitmproxy refreshes Content-Length itself when content is set.
    flow.response.headers.pop("content-encoding", None)
    flow.response.headers.pop("content-length", None)
    for key, value in headers.items():
        flow.response.headers[key] = value


def _log_request(flow: http.HTTPFlow, decision) -> None:
    if not should_log_request(flow):
        return
    try:
        data = build_request_data(flow)
        data["enforcement"] = decision.as_log_dict()
        pretty_print(f"{flow.request.method} {flow.request.host}", data)
    except Exception:
        return
