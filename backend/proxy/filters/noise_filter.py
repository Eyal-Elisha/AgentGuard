"""Detects telemetry, background, and upgrade traffic to avoid noisy enforcement."""

from __future__ import annotations

from mitmproxy import http
from urllib.parse import urlparse

from backend.proxy.config.noise_config import PATH_NOISE_KEYWORDS

from .noise.blocklist import _host_has_noise_token as _host_has_noise_token_impl
from .noise.blocklist import _tokenize_host as _tokenize_host_impl
from .noise.blocklist import is_in_blocklist as is_in_blocklist_impl
from .noise.easyprivacy import EASYPRIVACY_DOMAINS
from .noise.easyprivacy import _host_matches_easyprivacy as _host_matches_easyprivacy_impl
from .noise.easyprivacy import _thread
from .noise.easyprivacy import load_easyprivacy_domains as load_easyprivacy_domains_impl


def load_easyprivacy_domains():
    """Public facade kept for backward-compatible imports."""
    return load_easyprivacy_domains_impl()


def _host_matches_easyprivacy(host: str) -> bool:
    """Public facade kept for backward-compatible imports."""
    return _host_matches_easyprivacy_impl(host)


def _tokenize_host(host: str):
    """Public facade kept for backward-compatible imports."""
    return _tokenize_host_impl(host)


def _host_has_noise_token(host: str) -> bool:
    """Public facade kept for backward-compatible imports."""
    return _host_has_noise_token_impl(host)


def is_in_blocklist(host: str) -> bool:
    """Public facade kept for backward-compatible imports."""
    return is_in_blocklist_impl(host)


def is_upgrade_request(flow: http.HTTPFlow) -> bool:
    connection = flow.request.headers.get("connection", "").lower()
    upgrade = flow.request.headers.get("upgrade", "").lower()

    return "upgrade" in connection or upgrade == "websocket"


def is_noise(flow: http.HTTPFlow) -> bool:

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

    for kw in PATH_NOISE_KEYWORDS:
        if kw in path:
            return True

    report_header = flow.request.headers.get("report-to") or flow.request.headers.get("nel")
    if report_header:
        return True

    return False


__all__ = [
    "EASYPRIVACY_DOMAINS",
    "load_easyprivacy_domains",
    "_host_matches_easyprivacy",
    "_tokenize_host",
    "_host_has_noise_token",
    "is_in_blocklist",
    "is_upgrade_request",
    "is_noise",
]
