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
    except Exception:
        dest = ""
    return dest in _SEC_FETCH_SUBRESOURCES
