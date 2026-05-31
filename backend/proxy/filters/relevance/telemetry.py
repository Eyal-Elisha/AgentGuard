"""Detect telemetry, ads, and tracking endpoints."""

from __future__ import annotations

from mitmproxy import http

from .request_info import host, path

_TRACKING_HOST_PARTS = (
    "posthog.com",
    "google-analytics.com",
    "googletagmanager.com",
    "adtrafficquality.google",
    "doubleclick.net",
    "ad-delivery.net",
    "adform.net",
    "applovin.com",
    "dotomi.com",
    "creativecdn.com",
    "facebook.com",
    "graph.facebook.com",
    "pinterest.com",
    "securepubads.g.doubleclick.net",
)

_TRACKING_PATH_PARTS = (
    "/collect",
    "/g/collect",
    "/tr",
    "/scribe_logs",
    "/pixel",
    "/px.gif",
    "/cm-notify",
    "/cookie/match",
    "/v0/e/",
    "/flags/",
    "/array/",
    "/tag/js/",
    "/pagead/",
    "/pubads",
)


def is_tracking_or_telemetry(flow: http.HTTPFlow) -> bool:
    request_host = host(flow)
    request_path = path(flow)

    if any(part in request_host for part in _TRACKING_HOST_PARTS):
        return any(part in request_path for part in _TRACKING_PATH_PARTS)

    return any(part in request_path for part in _TRACKING_PATH_PARTS)
