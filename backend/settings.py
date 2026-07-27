"""Shared runtime settings for the AgentGuard backend and proxy addon."""

from __future__ import annotations

import logging
import os
from enum import Enum
from pathlib import Path
from urllib.parse import urlunsplit

from dotenv import load_dotenv

_logger = logging.getLogger(__name__)
_BACKEND_DIR = Path(__file__).resolve().parent
_LOADED = False

_ENV_API_HOST = "API_HOST"
_ENV_API_PORT = "API_PORT"
_ENV_PROXY_PORT = "PROXY_PORT"
_ENV_TIMEOUT_SECONDS = "AGENTGUARD_BACKEND_TIMEOUT_SECONDS"
_ENV_FAILURE_MODE = "AGENTGUARD_BACKEND_FAILURE_MODE"
_ENV_AUDIT_LOG_PATH = "AGENTGUARD_AUDIT_LOG_PATH"
_ENV_LOG_ENCRYPTION_KEY = "AGENTGUARD_LOG_ENCRYPTION_KEY"
_ENV_FRONTEND_URL = "AGENTGUARD_FRONTEND_URL"
_ENV_FRONTEND_PORT = "FRONTEND_PORT"
_DEFAULT_API_HOST = "127.0.0.1"
_DEFAULT_API_PORT = 3000
_DEFAULT_PROXY_PORT = 8080
_DEFAULT_FRONTEND_PORT = 5173
_DEFAULT_TIMEOUT_SECONDS = 10.0


class BackendFailureMode(str, Enum):
    FAIL_CLOSED = "fail_closed"
    FAIL_OPEN = "fail_open"


def load_settings_env() -> None:
    """Populate unset process env vars from backend/.env exactly once."""
    global _LOADED
    if _LOADED:
        return
    load_dotenv(_BACKEND_DIR / ".env", override=False)
    _LOADED = True


def get_api_port() -> int:
    load_settings_env()
    # Prefer API_PORT for the proxy decision URL; fall back to PORT so one env var
    # can drive both Flask (config.server_port) and the addon.
    raw = (os.getenv(_ENV_API_PORT) or os.getenv("PORT") or "").strip()
    return _validated_port(raw, env_name=_ENV_API_PORT, default_port=_DEFAULT_API_PORT)


def get_api_host() -> str:
    load_settings_env()
    return (os.getenv(_ENV_API_HOST) or "").strip() or _DEFAULT_API_HOST


def get_proxy_port() -> int:
    load_settings_env()
    raw = (os.getenv(_ENV_PROXY_PORT) or "").strip()
    return _validated_port(raw, env_name=_ENV_PROXY_PORT, default_port=_DEFAULT_PROXY_PORT)


def _validated_port(raw: str, *, env_name: str, default_port: int) -> int:
    if not raw:
        return default_port
    try:
        port = int(raw)
    except ValueError:
        _logger.warning(
            "[AgentGuard] Invalid %s=%r; falling back to %s",
            env_name,
            raw,
            default_port,
        )
        return default_port
    if not (1 <= port <= 65535):
        _logger.warning(
            "[AgentGuard] Out-of-range %s=%r; falling back to %s",
            env_name,
            raw,
            default_port,
        )
        return default_port
    return port


def get_backend_decision_url() -> str:
    """Return the local backend decision endpoint derived from the backend API port."""
    return urlunsplit(
        (
            "http",
            f"{get_api_host()}:{get_api_port()}",
            "/api/proxy/decision",
            "",
            "",
        )
    )


def get_backend_timeout_seconds() -> float:
    load_settings_env()
    raw = (os.getenv(_ENV_TIMEOUT_SECONDS) or "").strip()
    if not raw:
        return _DEFAULT_TIMEOUT_SECONDS
    try:
        timeout = float(raw)
    except ValueError:
        _logger.warning(
            "[AgentGuard] Invalid %s=%r; falling back to %.1fs",
            _ENV_TIMEOUT_SECONDS,
            raw,
            _DEFAULT_TIMEOUT_SECONDS,
        )
        return _DEFAULT_TIMEOUT_SECONDS
    if timeout <= 0:
        _logger.warning(
            "[AgentGuard] Non-positive %s=%r; falling back to %.1fs",
            _ENV_TIMEOUT_SECONDS,
            raw,
            _DEFAULT_TIMEOUT_SECONDS,
        )
        return _DEFAULT_TIMEOUT_SECONDS
    return timeout


def get_backend_failure_mode() -> BackendFailureMode:
    load_settings_env()
    raw = (os.getenv(_ENV_FAILURE_MODE) or "").strip().lower()
    if not raw:
        return BackendFailureMode.FAIL_CLOSED
    try:
        return BackendFailureMode(raw)
    except ValueError:
        _logger.warning(
            "[AgentGuard] Invalid %s=%r; falling back to %s",
            _ENV_FAILURE_MODE,
            raw,
            BackendFailureMode.FAIL_CLOSED.value,
        )
        return BackendFailureMode.FAIL_CLOSED


def get_frontend_port() -> int:
    load_settings_env()
    raw = (os.getenv(_ENV_FRONTEND_PORT) or "").strip()
    return _validated_port(raw, env_name=_ENV_FRONTEND_PORT, default_port=_DEFAULT_FRONTEND_PORT)


def get_dashboard_url() -> str:
    """Return the AgentGuard dashboard URL used as the 'go back' destination.

    Resolution order:
      1. `AGENTGUARD_FRONTEND_URL` if set (full URL override).
      2. `http://<api_host>:<FRONTEND_PORT>` — same FRONTEND_PORT var Vite uses,
         default 5173. Set `FRONTEND_PORT` in backend/.env to match your dev server.

    Loopback (`127.0.0.1`, ``localhost``, ``::1``, ``0.0.0.0``) is normalized to
    ``localhost`` so “Go back to safety” matches the URL you usually open in
    the browser (e.g. ``http://localhost:5000/``).
    """
    load_settings_env()
    raw = (os.getenv(_ENV_FRONTEND_URL) or "").strip()
    if raw:
        return _normalize_dashboard_url_host(raw)
    port = get_frontend_port()
    host = _dashboard_link_host(get_api_host())
    return urlunsplit(("http", f"{host}:{port}", "/", "", ""))


def _dashboard_link_host(api_host: str) -> str:
    h = (api_host or "").lower().strip()
    if h in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return "localhost"
    return api_host or "localhost"


def _normalize_dashboard_url_host(url: str) -> str:
    parts = urlsplit(url.strip())
    hostname = parts.hostname
    if not hostname:
        return url
    new_host = _dashboard_link_host(hostname)
    try:
        port = parts.port
    except ValueError:
        port = None
    if port is None:
        netloc = new_host
    else:
        netloc = f"{new_host}:{port}"
    path = parts.path if parts.path else "/"
    return urlunsplit((parts.scheme or "http", netloc, path, parts.query, parts.fragment))


def get_audit_log_path() -> Path:
    load_settings_env()
    raw = (os.getenv(_ENV_AUDIT_LOG_PATH) or "").strip()
    if raw:
        path = Path(raw).expanduser()
        if path.is_absolute():
            return path
        return (_BACKEND_DIR.parent / path).resolve()
    return _BACKEND_DIR.parent / "logs" / "agentguard_audit.jsonl"


def get_log_encryption_key() -> str:
    load_settings_env()
    key = (os.getenv(_ENV_LOG_ENCRYPTION_KEY) or "").strip()
    if not key:
        raise RuntimeError(
            "AGENTGUARD_LOG_ENCRYPTION_KEY must be set before persisting logs. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    return key


# ---------------------------------------------------------------------------
# Runtime passive-mode flag (in-memory; resets on backend restart)
# ---------------------------------------------------------------------------
_passive_mode: bool = False


def get_passive_mode() -> bool:
    return _passive_mode


def set_passive_mode(value: bool) -> None:
    global _passive_mode
    _passive_mode = value
