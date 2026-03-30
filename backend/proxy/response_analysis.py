"""Stage A in the mitmproxy addon: evaluate when the HTML response is available.

Typical flow: browser GET → server returns HTML → `response` hook runs with the page body.
That is *before* the next user/agent action on that document (typing, submitting). Rules that
need DOM (forms, text) run here.

A separate problem is POST/PUT that *already carry* secrets in the body: those are handled by
the request-time backend enforcement path. This module only scores from the response body for
eligible HTML flows.
"""

from __future__ import annotations

import logging

from mitmproxy import http

from backend.analysis.rules import EvaluationResult

from backend.proxy.filters.response_eligibility import is_eligible_for_response_analysis
from backend.proxy.rule_engine import evaluate_http_payload

_logger = logging.getLogger(__name__)


def _looks_like_navigation(flow: http.HTTPFlow) -> bool:
    headers = flow.request.headers
    sec_fetch_dest = headers.get("sec-fetch-dest", "").lower()
    sec_fetch_mode = headers.get("sec-fetch-mode", "").lower()
    upgrade = headers.get("upgrade-insecure-requests", "").strip()
    accept = headers.get("accept", "").lower()
    if sec_fetch_dest == "document" or sec_fetch_mode == "navigate" or upgrade == "1":
        return True
    if "text/html" in accept or "application/xhtml+xml" in accept:
        return True
    return False


def analyze_response(flow: http.HTTPFlow) -> EvaluationResult | None:
    _logger.debug(f"[AgentGuard] analyze_response called for url={flow.request.pretty_url}")
    eligible = is_eligible_for_response_analysis(flow)
    _logger.debug(f"[AgentGuard] is_eligible_for_response_analysis => {eligible}")
    if not flow.response:
        _logger.debug(f"[AgentGuard] no flow.response for url={flow.request.pretty_url}")
        return None

    headers = dict(flow.response.headers)
    body = flow.response.content or b""

    

    _logger.debug(f"[AgentGuard] analyze_response: url={flow.request.pretty_url} status={getattr(flow.response,'status_code',None)} body_len={len(body)}")

    # If not eligible (for example status != 2xx) but this looks like a navigation
    # and the body is missing, attempt a refetch to obtain HTML for analysis.
    try:
        status = flow.response.status_code
    except Exception:
        status = None

    print(f"[AgentGuard] analyze_response entry url={flow.request.pretty_url} eligible={eligible} status={status} body_len={len(body)}")

    if (not eligible) and (not body or not (200 <= (status or 0) < 300)) and _looks_like_navigation(flow):
        _logger.info(f"[AgentGuard] flow not eligible but looks like navigation; attempting refetch for analysis url={flow.request.pretty_url}")
        print(f"[AgentGuard] REFETCH START (pre-eligibility) url={flow.request.pretty_url}")
        try:
            import requests
            from requests.exceptions import SSLError, RequestException

            refetch_headers = dict(flow.request.headers)
            for h in ("if-none-match", "if-modified-since", "if-match", "if-unmodified-since", "etag"):
                refetch_headers.pop(h, None)
            refetch_headers.setdefault("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

            session = requests.Session()
            session.trust_env = False
            session.proxies = {}

            try:
                r = session.get(flow.request.pretty_url, headers=refetch_headers, timeout=5, verify=True)
                _logger.debug("[AgentGuard] pre-elig refetch attempt (verify=True) completed")
            except SSLError as e:
                _logger.warning("[AgentGuard] pre-elig refetch SSL verify failed, retrying with verify=False: %s", e)
                try:
                    r = session.get(flow.request.pretty_url, headers=refetch_headers, timeout=5, verify=False)
                    _logger.debug("[AgentGuard] pre-elig refetch attempt (verify=False) completed")
                except RequestException as e2:
                    _logger.exception("[AgentGuard] pre-elig refetch failed (verify=False): %s", e2)
                    r = None
            except RequestException as e:
                _logger.exception("[AgentGuard] pre-elig refetch failed: %s", e)
                r = None

            if r is not None:
                preview = (getattr(r, 'content', b'')[:500] or b'').decode('utf-8', errors='replace')
                print(f"[AgentGuard] REFETCH RESULT (pre-elig) status={getattr(r,'status_code',None)} len={len(getattr(r,'content',b''))} preview={preview[:300]!r}")
                if getattr(r, 'status_code', None) == 200 and getattr(r, 'content', None):
                    body = r.content
                    headers = {**headers, **{k: v for k, v in r.headers.items()}}
                    eligible = True
        except Exception as e:
            print(f"[AgentGuard] REFETCH ERROR (pre-elig): {e}")
            _logger.exception("[AgentGuard] pre-elig refetch for analysis failed: %s", e)

    if (not body) and _looks_like_navigation(flow) and eligible:
        _logger.info(f"[AgentGuard] empty response body detected for navigation url={flow.request.pretty_url}, attempting refetch for analysis")
        print(f"[AgentGuard] REFETCH START url={flow.request.pretty_url}")
        try:
            import requests
            from requests.exceptions import SSLError, RequestException

            refetch_headers = dict(flow.request.headers)
            for h in ("if-none-match", "if-modified-since", "if-match", "if-unmodified-since", "etag"):
                refetch_headers.pop(h, None)

            refetch_headers.setdefault("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

            _logger.debug(f"[AgentGuard] refetch headers keys={list(refetch_headers.keys())}")

            session = requests.Session()
            session.trust_env = False
            session.proxies = {}

            try:
                r = session.get(flow.request.pretty_url, headers=refetch_headers, timeout=5, verify=True)
                _logger.debug("[AgentGuard] refetch attempt (verify=True) completed")
            except SSLError as e:
                _logger.warning("[AgentGuard] refetch SSL verification failed, retrying with verify=False: %s", e)
                try:
                    r = session.get(flow.request.pretty_url, headers=refetch_headers, timeout=5, verify=False)
                    _logger.debug("[AgentGuard] refetch attempt (verify=False) completed")
                except RequestException as e2:
                    _logger.exception("[AgentGuard] refetch failed (verify=False): %s", e2)
                    r = None
            except RequestException as e:
                _logger.exception("[AgentGuard] refetch failed: %s", e)
                r = None

            if r is not None:
                preview = (getattr(r, 'content', b'')[:500] or b'').decode('utf-8', errors='replace')
                print(f"[AgentGuard] REFETCH RESULT status={getattr(r,'status_code',None)} len={len(getattr(r,'content',b''))} preview={preview[:300]!r}")
                _logger.info(f"[AgentGuard] refetch returned status={getattr(r,'status_code',None)} content_len={len(getattr(r,'content',b''))}")
                if getattr(r, 'status_code', None) == 200 and getattr(r, 'content', None):
                    body = r.content
                    # Merge response headers: prefer origin headers from the refetch for features
                    headers = {**headers, **{k: v for k, v in r.headers.items()}}
        except Exception as e:
            print(f"[AgentGuard] REFETCH ERROR: {e}")
            _logger.exception("[AgentGuard] refetch for analysis failed, falling back to available response: %s", e)

    return evaluate_http_payload(
        url=flow.request.pretty_url,
        method=flow.request.method,
        headers=headers,
        body=body,
    )
    _logger.debug(f"[AgentGuard] analysis complete url={flow.request.pretty_url} decision={getattr(result,'decision',None)} risk={getattr(result,'risk_score',None)} rules={len(getattr(result,'rule_results',[]))}")

    return result


def analyze_response_safe(flow: http.HTTPFlow) -> EvaluationResult | None:
    try:
        return analyze_response(flow)
      
    except Exception:
        _logger.exception("[AgentGuard] Stage A failed in safe wrapper")
        return None

