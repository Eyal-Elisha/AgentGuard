"""Detect non-navigation requests that are likely user actions."""

from __future__ import annotations

from mitmproxy import http

from .request_info import header, method, path

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


def is_meaningful_user_action(flow: http.HTTPFlow) -> bool:
    if method(flow) not in _ACTION_METHODS:
        return False

    content_type = header(flow, "content-type").lower()
    if any(item in content_type for item in _ACTION_CONTENT_TYPES):
        return True

    return any(hint in path(flow) for hint in _SENSITIVE_PATH_HINTS)
