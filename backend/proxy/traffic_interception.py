"""Mitmproxy addon: enforce backend request decisions and run Stage A on eligible responses."""

from __future__ import annotations

from mitmproxy import http

from backend.proxy.addon import handle_request, handle_response
from backend.proxy.audit import ensure_proxy_session_started
from backend.settings import load_settings_env

load_settings_env()

# For now, proxy activation itself marks the start of the active BrowserOS session.
# A future frontend activation button should call into the same session-start flow.
ensure_proxy_session_started()


def request(flow: http.HTTPFlow):
    handle_request(flow)


def response(flow: http.HTTPFlow):
    handle_response(flow)
