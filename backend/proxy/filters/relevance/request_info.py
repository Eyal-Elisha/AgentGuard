"""Small request helpers shared by relevance filters."""

from __future__ import annotations

from urllib.parse import urlparse

from mitmproxy import http


def header(flow: http.HTTPFlow, name: str) -> str:
    try:
        return flow.request.headers.get(name, "")
    except Exception:
        return ""


def method(flow: http.HTTPFlow) -> str:
    try:
        return flow.request.method.upper()
    except Exception:
        return ""


def host(flow: http.HTTPFlow) -> str:
    try:
        return (flow.request.host or "").lower()
    except Exception:
        return ""


def url(flow: http.HTTPFlow) -> str:
    try:
        return flow.request.pretty_url or ""
    except Exception:
        return ""


def path(flow: http.HTTPFlow) -> str:
    try:
        return urlparse(url(flow)).path.lower()
    except Exception:
        return ""
