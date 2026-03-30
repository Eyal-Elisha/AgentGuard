from __future__ import annotations

from mitmproxy import http


def is_html_response(flow: http.HTTPFlow) -> bool:
    if not flow.response:
        return False
    ct = flow.response.headers.get("content-type", "").lower()
    return "text/html" in ct


def is_binary_media_response(flow: http.HTTPFlow) -> bool:
    if not flow.response:
        return False
    ct = flow.response.headers.get("content-type", "").lower()
    return bool(
        ct.startswith("image/")
        or ct.startswith("font/")
        or ct.startswith("video/")
        or ct.startswith("audio/")
    )
