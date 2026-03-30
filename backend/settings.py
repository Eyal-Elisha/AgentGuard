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
_DEFAULT_API_HOST = "127.0.0.1"
_DEFAULT_API_PORT = 3000
_DEFAULT_PROXY_PORT = 8080
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


def get_audit_log_path() -> Path:
    load_settings_env()
    raw = (os.getenv(_ENV_AUDIT_LOG_PATH) or "").strip()
    if raw:
        path = Path(raw).expanduser()
        if path.is_absolute():
            return path
        return (_BACKEND_DIR.parent / path).resolve()
    return _BACKEND_DIR.parent / "logs" / "agentguard_audit.jsonl"
