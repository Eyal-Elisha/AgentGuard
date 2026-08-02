"""Detects telemetry, background, and upgrade traffic to avoid noisy enforcement."""

from __future__ import annotations

from urllib.parse import urlparse

from mitmproxy import http

from backend.proxy.config.noise_config import PATH_NOISE_KEYWORDS

from .noise.blocklist import is_in_blocklist


def is_upgrade_request(flow: http.HTTPFlow) -> bool:
    connection = flow.request.headers.get("connection", "").lower()
    upgrade = flow.request.headers.get("upgrade", "").lower()
    return "upgrade" in connection or upgrade == "websocket"


def is_noise(flow: http.HTTPFlow) -> bool:
    """Whether this flow is background chatter rather than something the user did.

    The host checks come first because they are the cheapest and catch the
    most: known trackers, then EasyPrivacy, then telemetry-ish path keywords.
    A `Report-To` or `NEL` header means the browser is reporting on itself.
    """
    try:
        host = (flow.request.host or "").lower()
    except Exception:
        host = ""
    if is_in_blocklist(host):
        return True

    if is_upgrade_request(flow):
        return True

    try:
        path = urlparse(flow.request.pretty_url or "").path.lower()
    except Exception:
        path = ""
    if any(keyword in path for keyword in PATH_NOISE_KEYWORDS):
        return True

    return bool(flow.request.headers.get("report-to") or flow.request.headers.get("nel"))
