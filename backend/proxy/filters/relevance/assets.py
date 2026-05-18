"""Detect static resources that should not become analysis events."""

from __future__ import annotations

from mitmproxy import http

from backend.proxy.filters.sec_fetch_filter import sec_fetch_is_subresource
from backend.proxy.filters.static_filter import is_likely_static_subresource

from .request_info import path, url

_STATIC_EXACT_PATHS = {
    "/favicon.ico",
    "/manifest.json",
    "/robots.txt",
    "/sw.js",
    "/service-worker.js",
}

_STATIC_PATH_PARTS = (
    "/public/assets/",
    "/public/font/",
    "/docs-images-rt/",
    "/assets/images/",
    "/rsrc.php/",
    "/static_resources/webworker",
)


def is_static_or_subresource(flow: http.HTTPFlow) -> bool:
    request_path = path(flow)
    if request_path in _STATIC_EXACT_PATHS:
        return True

    if any(part in request_path for part in _STATIC_PATH_PARTS):
        return True

    if request_path.endswith(("/sw.js", "/service-worker.js")):
        return True

    if is_likely_static_subresource(url(flow)):
        return True

    return sec_fetch_is_subresource(flow)
