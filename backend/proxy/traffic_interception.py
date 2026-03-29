"""Mitmproxy addon: enforce backend request decisions and run Stage A on eligible responses."""

from __future__ import annotations

from mitmproxy import http

from backend.proxy.addon import handle_request, handle_response
from backend.settings import load_settings_env

load_settings_env()


def request(flow: http.HTTPFlow):
    handle_request(flow)


def response(flow: http.HTTPFlow):
    handle_response(flow)
