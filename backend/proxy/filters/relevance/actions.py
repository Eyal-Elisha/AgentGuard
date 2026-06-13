"""Detect non-navigation requests that are likely user actions."""

from __future__ import annotations

from mitmproxy import http

from backend.proxy.filters.static_filter import is_likely_static_subresource

from .request_info import header, method, path, url

_ACTION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_ACTION_CONTENT_TYPES = (
    "application/json",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
)
_SENSITIVE_PATH_HINTS = (
    "login",
    "signin",
    "signup",
    "auth",
    "checkout",
    "payment",
    "account",
    "password",
)


def _is_same_site_json_get(flow: http.HTTPFlow) -> bool:
    """SPA/API reads on the page's own origin — not third-party ad or tracker XHR."""
    if method(flow) != "GET":
        return False
    accept = header(flow, "accept").lower()
    if "application/json" not in accept or is_likely_static_subresource(url(flow)):
        return False
    site = header(flow, "sec-fetch-site").lower()
    return site in ("same-origin", "same-site")


def is_meaningful_user_action(flow: http.HTTPFlow) -> bool:
    if _is_same_site_json_get(flow):
        return True

    if method(flow) not in _ACTION_METHODS:
        return False

    content_type = header(flow, "content-type").lower()
    if any(item in content_type for item in _ACTION_CONTENT_TYPES):
        return True

    return any(hint in path(flow) for hint in _SENSITIVE_PATH_HINTS)
