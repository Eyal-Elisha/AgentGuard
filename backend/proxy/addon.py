from __future__ import annotations

from mitmproxy import http

from backend.analysis.rules import Decision
from backend.custom_blacklist import custom_blacklist_matches
from backend.proxy.enforcement import (
    build_browseros_block_response,
    build_block_response,
    build_enforcement_response,
    build_warn_body,
    build_warn_response,
    is_backend_failure_source,
    local_rule_block_decision,
)
from backend.proxy.filter_logging import should_log_request, should_log_response
from backend.proxy.filter_requests import should_forward
from backend.proxy.filters.response_eligibility_filter import should_ignore_response
from backend.proxy.request_decision import fetch_backend_decision
from backend.proxy.response_decision import fetch_backend_response_decision
from backend.proxy.rule_engine import get_custom_blacklist
from backend.proxy.utils import build_request_data, build_response_payload, pretty_print
from backend.proxy.warn_bypass import (
    BYPASS_QUERY_PARAM,
    consume_bypass_token,
    register_continue_anyway,
    should_suppress_warn_interstitial,
)


_ADDON_VERSION = "addon@continue-anyway-ui-suppress-v1"


def _diag(message: str) -> None:
    """Write a diagnostic line to stdout so it lands in .agentguard/mitmweb.log.

    mitmproxy's stdout is redirected to that file by `proxy_launcher.py`.
    We avoid `logging.info` because mitmproxy doesn't install an INFO-level
    handler on the root logger by default, so those messages get swallowed.

    On Windows mitmweb's stdout defaults to cp1252; printing a character
    outside that codepage raises `UnicodeEncodeError`, which previously
    aborted `handle_request` mid-flight and prevented the bypass 302 from
    being sent. We force ASCII-safe output to avoid that whole class of bug.
    """
    safe = message.encode("ascii", errors="replace").decode("ascii")
    print(f"[AgentGuard] {safe}", flush=True)


_diag(f"loaded {_ADDON_VERSION}")


def _strip_query_param(url: str, param: str) -> str:
    """Return `url` with all occurrences of query parameter `param` removed."""
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    parts = urlsplit(url)
    pairs = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != param]
    new_query = urlencode(pairs, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def _is_get_navigation(flow: http.HTTPFlow) -> bool:
    """Warn interstitial only makes sense for navigations the browser can render."""
    return flow.request.method.upper() == "GET"


def _agent_name_from_flow(flow: http.HTTPFlow) -> str | None:
    value = flow.request.headers.get("x-agentguard-agent") or flow.request.headers.get("x-agent-name")
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def _is_browseros_agent(flow: http.HTTPFlow) -> bool:
    agent_name = _agent_name_from_flow(flow)
    if not agent_name:
        return False
    return agent_name.casefold().replace(" ", "") == "browseros"


def _make_block_response(flow: http.HTTPFlow, decision):
    """Pick the rendered Block response: HTML interstitial for GET
    navigations (browser will display it), plain 403 text otherwise
    (XHR / sub-resource / non-navigation requests can't render HTML)."""
    if _is_browseros_agent(flow) and not is_backend_failure_source(decision.source):
        return build_browseros_block_response(
            original_url=flow.request.pretty_url,
            decision=decision,
        )
    if _is_get_navigation(flow):
        return build_block_response(
            original_url=flow.request.pretty_url,
            decision=decision,
        )
    return build_enforcement_response(decision)


# Last passive-mode value received from a healthy backend response.
# Used as a fallback when the backend is temporarily unreachable so that a
# passive-mode session doesn't suddenly start blocking all traffic.
_cached_passive_mode: bool = False

_BACKEND_FAILURE_SOURCES = frozenset({
    "backend_unreachable",
    "backend_timeout",
    "backend_error",
})


def _maybe_redeem_bypass_token(flow: http.HTTPFlow) -> bool:
    """If the request carries `_agentguard_bypass=<token>` in the query
    string AND the token validates for this host:

    * register a continue-anyway profile for this navigation (suppress the
      warn interstitial only for the redirect follow-up / short subresource
      window; the backend still runs on every request),
    * respond with a 302 redirect to the same URL with the token stripped,
      so the browser's address bar never lingers on the token URL,
    * return True so the caller knows the request was handled.

    Returns False when no token was present, the token was stale/unknown,
    or it was minted for a different host.
    """
    token = flow.request.query.get(BYPASS_QUERY_PARAM) if BYPASS_QUERY_PARAM in flow.request.query else None
    if not token:
        return False

    matched_host = consume_bypass_token(token)
    if matched_host is None:
        _diag(
            f"bypass token in URL for {flow.request.host} is stale/unknown - "
            f"stripping and falling through to normal evaluation"
        )
        # Strip the param so the origin and downstream code never see it.
        if BYPASS_QUERY_PARAM in flow.request.query:
            flow.request.query.pop(BYPASS_QUERY_PARAM, None)
        return False

    if matched_host.lower() != (flow.request.host or "").lower():
        _diag(
            f"bypass token host mismatch (minted for {matched_host}, "
            f"request to {flow.request.host}) - refusing"
        )
        if BYPASS_QUERY_PARAM in flow.request.query:
            flow.request.query.pop(BYPASS_QUERY_PARAM, None)
        return False

    # Token is valid for this host — allow the real page to render without a
    # warn loop, but keep evaluating and logging subsequent traffic.
    clean_url = _strip_query_param(flow.request.pretty_url, BYPASS_QUERY_PARAM)
    register_continue_anyway(flow.request.host, clean_url)
    _diag(
        f"bypass token redeemed for {flow.request.host} -> 302 to {clean_url}"
    )
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
    global _cached_passive_mode

    # Custom blacklist hits that aren't high-signal enough to forward to the
    # backend (`should_forward` returns False for them) are blocked locally so
    # the user still gets a deterministic enforcement response.
    if custom_blacklist_matches(flow.request.host, flow.request.pretty_url, get_custom_blacklist()):
        if not should_forward(flow):
            decision = local_rule_block_decision(
                rule_id="custom_blacklist",
                explanation=f"URL '{flow.request.pretty_url}' matches the custom local blacklist",
                source="proxy_custom_blacklist",
            )
            flow.metadata["agentguard_enforcement"] = decision.as_log_dict()
            flow.response = _make_block_response(flow, decision)
            _log_request(flow, decision)
            return

    if not should_forward(flow):
        return

    # Stage 1: redeem a one-shot bypass token (`?_agentguard_bypass=...`).
    if _maybe_redeem_bypass_token(flow):
        return

    decision = fetch_backend_decision(flow)

    # Update cached passive-mode only when the backend responded successfully.
    if decision.source == "backend":
        _cached_passive_mode = decision.passive_mode

    # When the backend is unreachable and the session was in passive mode,
    # pass the request through silently instead of failing closed.
    if decision.source in _BACKEND_FAILURE_SOURCES and _cached_passive_mode:
        return

    flow.metadata["agentguard_forwarded_to_backend"] = True
    flow.metadata["agentguard_enforcement"] = decision.as_log_dict()

    _log_request(flow, decision)

    if decision.decision == Decision.BLOCK and not decision.passive_mode:
        flow.response = _make_block_response(flow, decision)
        return

    if (
        decision.decision == Decision.WARN
        and not decision.passive_mode
        and _is_get_navigation(flow)
    ):
        if should_suppress_warn_interstitial(flow):
            flow.metadata["agentguard_suppressed_warn_ui"] = True
            _diag(
                f"WARN for {flow.request.host} but interstitial suppressed "
                f"(continue anyway profile) - forwarding to origin"
            )
        else:
            flow.response = build_warn_response(
                original_url=flow.request.pretty_url,
                host=flow.request.host,
                decision=decision,
            )
            _diag(f"served WARN interstitial for {flow.request.host}")


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

    if (
        decision.decision == Decision.WARN
        and not decision.passive_mode
        and _is_get_navigation(flow)
    ):
        if flow.metadata.get("agentguard_suppressed_warn_ui") or should_suppress_warn_interstitial(
            flow
        ):
            _diag(
                f"WARN at response-time for {flow.request.host} but interstitial "
                f"suppressed - leaving origin body intact"
            )
            return
        _diag(
            f"served WARN at response-time for {flow.request.host} "
            f"(replacing body of {flow.response.status_code} response)"
        )
        body, headers = build_warn_body(
            original_url=flow.request.pretty_url,
            host=flow.request.host,
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
