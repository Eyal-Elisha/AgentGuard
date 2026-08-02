"""Where each part of AgentGuard listens, and how the others reach it."""

from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

from .env import read_env, read_port

_DEFAULT_API_HOST = "127.0.0.1"
_DEFAULT_API_PORT = 3000
_DEFAULT_PROXY_PORT = 8080
_DEFAULT_FRONTEND_PORT = 5173

_LOOPBACK_HOSTNAMES = ("localhost", "127.0.0.1", "::1", "0.0.0.0")


def get_api_host() -> str:
    return read_env("API_HOST") or _DEFAULT_API_HOST


def get_api_port() -> int:
    """The backend API port, as the *proxy addon* resolves it.

    Prefers API_PORT, then falls back to PORT so a single variable can drive
    both the Flask server and the addon's decision URL.
    """
    raw = read_env("API_PORT") or read_env("PORT")
    return read_port(raw, env_name="API_PORT", default_port=_DEFAULT_API_PORT)


def server_port(default: int = 3000) -> int:
    """The port `app.run()` binds. PORT only — API_PORT is the addon's view."""
    raw = os.environ.get("PORT")
    if raw is None or not raw.strip():
        return default
    try:
        port = int(raw.strip())
    except ValueError:
        return default
    if port < 1 or port > 65535:
        return default
    return port


def get_proxy_port() -> int:
    return read_port(read_env("PROXY_PORT"), env_name="PROXY_PORT", default_port=_DEFAULT_PROXY_PORT)


def get_frontend_port() -> int:
    return read_port(
        read_env("FRONTEND_PORT"), env_name="FRONTEND_PORT", default_port=_DEFAULT_FRONTEND_PORT
    )


def get_backend_decision_url() -> str:
    """The endpoint the proxy addon POSTs every intercepted request to."""
    return urlunsplit(("http", f"{get_api_host()}:{get_api_port()}", "/api/proxy/decision", "", ""))


def get_dashboard_url() -> str:
    """Where "Go back to safety" on an interstitial sends the browser.

    `AGENTGUARD_FRONTEND_URL` overrides it outright. Otherwise it is the API
    host on FRONTEND_PORT — the same variable Vite uses.
    """
    override = read_env("AGENTGUARD_FRONTEND_URL")
    if override:
        return _normalize_url_host(override)
    return urlunsplit(("http", f"{_link_host(get_api_host())}:{get_frontend_port()}", "/", "", ""))


def _link_host(api_host: str) -> str:
    """Loopback in any spelling becomes `localhost`.

    The interstitial link should match the URL the user actually has open, and
    that is almost never `0.0.0.0`.
    """
    if (api_host or "").lower().strip() in _LOOPBACK_HOSTNAMES:
        return "localhost"
    return api_host or "localhost"


def _normalize_url_host(url: str) -> str:
    parts = urlsplit(url.strip())
    hostname = parts.hostname
    if not hostname:
        return url
    try:
        port = parts.port
    except ValueError:
        port = None
    host = _link_host(hostname)
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit((parts.scheme or "http", netloc, parts.path or "/", parts.query, parts.fragment))
