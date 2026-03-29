"""Criteria for Stage A on responses and for skipping noisy request/response logs."""

from __future__ import annotations

from urllib.parse import urlparse

from mitmproxy import http

from backend.proxy.filters.browser_filter import is_browser_user_agent
from backend.proxy.filters.noise_filter import is_noise

_STATIC_PATH_EXACT = frozenset({"/favicon.ico", "/robots.txt"})
_STATIC_SUFFIXES = (
    ".ico",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".bmp",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".js",
    ".css",
    ".mjs",
    ".map",
    ".mp4",
    ".webm",
    ".mp3",
    ".wav",
)
_SEC_FETCH_SKIP = frozenset({"image", "style", "script", "font"})


def _response_is_html(flow: http.HTTPFlow) -> bool:
    ct = flow.response.headers.get("content-type", "").lower() if flow.response else ""
    return "text/html" in ct


def _is_likely_static_subresource(url: str) -> bool:
    path = urlparse(url).path.lower()
    if path in _STATIC_PATH_EXACT:
        return True
    return path.endswith(_STATIC_SUFFIXES)


def _sec_fetch_is_subresource(flow: http.HTTPFlow) -> bool:
    dest = flow.request.headers.get("sec-fetch-dest", "").lower()
    return dest in _SEC_FETCH_SKIP


def _response_is_binary_media(flow: http.HTTPFlow) -> bool:
    if not flow.response:
        return False
    ct = flow.response.headers.get("content-type", "").lower()
    return bool(
        ct.startswith("image/")
        or ct.startswith("font/")
        or ct.startswith("video/")
        or ct.startswith("audio/")
    )


def should_log_request(flow: http.HTTPFlow) -> bool:
    """Skip noisy request logs for static paths and subresource fetches (aligned with Stage A)."""
    if _is_likely_static_subresource(flow.request.pretty_url):
        return False
    if _sec_fetch_is_subresource(flow):
        return False
    return True


def should_log_response(flow: http.HTTPFlow) -> bool:
    """Skip verbose response logs when we do not analyze the body (static/media/subresource)."""
    if not flow.response:
        return False
    if _is_likely_static_subresource(flow.request.pretty_url):
        return False
    if _sec_fetch_is_subresource(flow):
        return False
    if _response_is_binary_media(flow):
        return False
    return True


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


def is_eligible_for_response_analysis(flow: http.HTTPFlow) -> bool:
    """Full Stage A on response: 2xx HTML document, skip static subresources."""
    if not flow.response:
        return False
    if not (200 <= flow.response.status_code < 300):
        return False
    if _is_likely_static_subresource(flow.request.pretty_url):
        return False
    if _sec_fetch_is_subresource(flow):
        return False

    if is_browser_traffic(flow):
        return _response_is_html(flow)
    ua = flow.request.headers.get("user-agent", "")
    if not is_browser_user_agent(ua):
        return False
    if is_noise(flow):
        return False
    if flow.request.method.upper() != "GET":
        return False
    return _response_is_html(flow)
