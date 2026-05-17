"""Detect browser/app background traffic that is not user intent."""

from __future__ import annotations

from mitmproxy import http

from .request_info import host, path, url

_BACKGROUND_HOST_PARTS = (
    "config.extension.",
    "functional.events.data.microsoft.com",
    "play.google.com",
    "ssl.gstatic.com",
    "safebrowsing.googleapis.com",
    "suggestqueries.google.com",
    "1clickvpn.net",
    "screencastify.com",
    "grammarly.com",
    "f-log-extension.grammarly.io",
)

_BACKGROUND_PATH_PARTS = (
    "/signal_browser_extension/",
    "/backend-api/celsius/ws/",
    "/ces/statsc/",
    "/ces/v1/telemetry/",
    "/docos/p/sync",
    "/status.json",
    "/async/",
    "/complete/search",
    "/rotateboundcookies",
    "/dynamicconfig",
    "/browserplugin/config",
    "/bootloader-endpoint/",
    "/static_resources/",
    "/whatsapp_error_reports/",
    "/gen204/",
    "/logs",
    "/logservice/",
    "/netcheck.gif",
    "/geoip/",
)


def is_background_service_request(flow: http.HTTPFlow) -> bool:
    request_host = host(flow)
    request_path = path(flow)
    request_url = url(flow).lower()

    if any(part in request_host for part in _BACKGROUND_HOST_PARTS):
        return True

    if any(part in request_path for part in _BACKGROUND_PATH_PARTS):
        return True

    return "retry_count=" in request_url and "posthog" in request_host
