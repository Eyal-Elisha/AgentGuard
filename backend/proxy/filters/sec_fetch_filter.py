"""Uses Sec-Fetch headers to identify likely subresource requests."""

from __future__ import annotations

from mitmproxy import http

_SEC_FETCH_SUBRESOURCES = {
    "image",
    "style",
    "script",
    "font",
    "empty",
    "report",
    "embed",
    "object",
    "manifest",
}


def sec_fetch_is_subresource(flow: http.HTTPFlow) -> bool:
    try:
        dest = flow.request.headers.get("sec-fetch-dest", "").lower()
        mode = flow.request.headers.get("sec-fetch-mode", "").lower()
    except Exception:
        dest = ""
        mode = ""
    # Chrome sometimes sends dest=empty on real top-level navigations.
    if dest == "empty" and mode == "navigate":
        return False
    if dest == "empty" and flow.request.method.upper() == "GET":
        accept = flow.request.headers.get("accept", "").lower()
        if "application/json" in accept:
            return False
    return dest in _SEC_FETCH_SUBRESOURCES
