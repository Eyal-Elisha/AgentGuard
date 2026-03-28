from __future__ import annotations

import json
import datetime
import re
import sys
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

from mitmproxy import http

# Repo root so `backend.*` imports work when mitmweb loads this script from any cwd.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.feature_extraction.feature_extractor import FeatureExtractor
from backend.analysis.stages.stage_a.evaluator import StageAEvaluator
from backend.analysis.rules import EvaluationResult, RuleResult


# This is a part I did in order to redunce noise of other apps, and analysis that happen in the background while browsing,
# I think we have to make a separate ticket for this (the part I did in the scope ~~~~ ... ~~~~~)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

NOISE_DOMAINS = [
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "facebook.net",
    "analytics.tiktok.com",
    "bing.com",
    "bat.bing.com",
    "domainreliability",
    "go-mpulse.net",
    "akstat.io",
    "nr-data.net",
    "newrelic.com",
    "datadoghq.com",
    "hotjar.com",
    "segment.io",
    "mixpanel.com",
    "cdn-cgi",
    "cloudflare",
    "gstatic.com",
]

BROWSER_HEADERS = [
    "sec-fetch-site",
    "sec-fetch-mode",
    "sec-fetch-dest",
    "user-agent"
]

def is_browser_user_agent(user_agent: str) -> bool:

    if not user_agent:
        return False

    if "electron/" in user_agent.lower():
        return False

    browser_patterns = ["chrome/", "firefox/", "safari/", "edg/"]
    return any(re.search(pat, user_agent, re.IGNORECASE) for pat in browser_patterns)

def is_noise(flow: http.HTTPFlow) -> bool:
    host = flow.request.host.lower()
    url = flow.request.pretty_url.lower()

    if any(domain in host for domain in NOISE_DOMAINS):
        return True

    if "upgrade" in flow.request.headers.get("connection", "").lower():
        return True

    return False

def is_browser_traffic(flow: http.HTTPFlow) -> bool:
    ua = flow.request.headers.get("user-agent", "")
    if not is_browser_user_agent(ua):
        return False

    if is_noise(flow):
        return False

    method = flow.request.method.upper()
    has_body = bool(flow.request.content)

    if method in ["POST", "PUT", "PATCH"]:
        return True

    if method == "GET" and has_body:
        return True

    return False

# Typical subresources — not worth running HTML phishing rules (favicon 404s often still return text/html).
_STATIC_PATH_EXACT = frozenset({"/favicon.ico", "/robots.txt"})
_STATIC_SUFFIXES = (
    ".ico", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".js", ".css", ".mjs", ".map",
    ".mp4", ".webm", ".mp3", ".wav",
)
_SEC_FETCH_SKIP = frozenset({"image", "style", "script", "font"})


def _is_likely_static_subresource(url: str) -> bool:
    path = urlparse(url).path.lower()
    if path in _STATIC_PATH_EXACT:
        return True
    return path.endswith(_STATIC_SUFFIXES)


def is_eligible_for_analysis(flow: http.HTTPFlow) -> bool:
    """Browser traffic we actually want to score: successful responses, not favicon/CSS/JS, etc."""
    if not flow.response:
        return False
    # Error pages (404 HTML for missing favicon, etc.) are noisy and not the navigated document.
    if not (200 <= flow.response.status_code < 300):
        return False
    if _is_likely_static_subresource(flow.request.pretty_url):
        return False
    dest = flow.request.headers.get("sec-fetch-dest", "").lower()
    if dest in _SEC_FETCH_SKIP:
        return False

    if is_browser_traffic(flow):
        return True
    ua = flow.request.headers.get("user-agent", "")
    if not is_browser_user_agent(ua):
        return False
    if is_noise(flow):
        return False
    if flow.request.method.upper() != "GET":
        return False
    ct = flow.response.headers.get("content-type", "").lower()
    return "text/html" in ct

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

_extractor = FeatureExtractor()
_evaluator = StageAEvaluator()


def _evaluation_to_dict(result: EvaluationResult) -> Dict[str, Any]:
    def rule_dict(r: RuleResult) -> Dict[str, Any]:
        return {
            "rule_id": r.rule_id,
            "rule_type": r.rule_type.value,
            "score": r.score,
            "hard_block": r.hard_block,
            "explanation": r.explanation,
            "triggered": r.triggered,
        }

    return {
        "decision": result.decision.value,
        "risk_score": result.risk_score,
        "hard_block_triggered": result.hard_block_triggered,
        "stage_b_required": result.stage_b_required,
        "rule_results": [rule_dict(r) for r in result.rule_results],
    }


def pretty_print(title: str, data: Dict[str, Any]) -> None:
    print(f"\n===== {title} =====")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"===== End of {title} =====\n")


def response(flow: http.HTTPFlow) -> None:
    """After each response: extract features from the response body/headers, then Stage A evaluation.

    HTML and Content-Type are on the response; this matches `backend/app.py` and tests.
    """
    if not is_eligible_for_analysis(flow):
        return

    if not flow.response:
        return

    headers = dict(flow.response.headers)
    body = flow.response.content or b""
    features = _extractor.extract(
        url=flow.request.pretty_url,
        method=flow.request.method,
        headers=headers,
        body=body,
    )
    result = _evaluator.evaluate(features)
    payload = {
        "timestamp": str(datetime.datetime.now()),
        "phase": "response",
        "status_code": flow.response.status_code,
        "url": flow.request.pretty_url,
        "evaluation": _evaluation_to_dict(result),
    }
    pretty_print(f"EVAL {flow.response.status_code} {flow.request.host} (response)", payload)