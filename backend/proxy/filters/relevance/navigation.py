"""Detect user-visible navigations."""

from __future__ import annotations

from mitmproxy import http

from .request_info import header, method


def is_top_level_navigation(flow: http.HTTPFlow) -> bool:
    if method(flow) != "GET":
        return False

    dest = header(flow, "sec-fetch-dest").lower()
    mode = header(flow, "sec-fetch-mode").lower()
    upgrade = header(flow, "upgrade-insecure-requests")
    accept = header(flow, "accept").lower()

    if dest == "document" or mode == "navigate" or upgrade == "1":
        return True

    return "text/html" in accept
