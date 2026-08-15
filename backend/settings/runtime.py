"""How the proxy behaves at runtime, and where its audit trail is written."""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path

from .env import REPO_ROOT, read_env

_logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 10.0


class BackendFailureMode(str, Enum):
    """What the proxy does when the backend cannot be reached."""

    FAIL_CLOSED = "fail_closed"
    FAIL_OPEN = "fail_open"


def get_backend_timeout_seconds() -> float:
    """How long the proxy waits for a decision before giving up on it."""
    raw = read_env("AGENTGUARD_BACKEND_TIMEOUT_SECONDS")
    if not raw:
        return _DEFAULT_TIMEOUT_SECONDS
    try:
        timeout = float(raw)
    except ValueError:
        _logger.warning(
            "[AgentGuard] Invalid AGENTGUARD_BACKEND_TIMEOUT_SECONDS=%r; falling back to %.1fs",
            raw,
            _DEFAULT_TIMEOUT_SECONDS,
        )
        return _DEFAULT_TIMEOUT_SECONDS
    if timeout <= 0:
        _logger.warning(
            "[AgentGuard] Non-positive AGENTGUARD_BACKEND_TIMEOUT_SECONDS=%r; falling back to %.1fs",
            raw,
            _DEFAULT_TIMEOUT_SECONDS,
        )
        return _DEFAULT_TIMEOUT_SECONDS
    return timeout


def get_backend_failure_mode() -> BackendFailureMode:
    raw = read_env("AGENTGUARD_BACKEND_FAILURE_MODE").lower()
    if not raw:
        return BackendFailureMode.FAIL_CLOSED
    try:
        return BackendFailureMode(raw)
    except ValueError:
        _logger.warning(
            "[AgentGuard] Invalid AGENTGUARD_BACKEND_FAILURE_MODE=%r; falling back to %s",
            raw,
            BackendFailureMode.FAIL_CLOSED.value,
        )
        return BackendFailureMode.FAIL_CLOSED


def get_audit_log_path() -> Path:
    raw = read_env("AGENTGUARD_AUDIT_LOG_PATH")
    if not raw:
        return REPO_ROOT / "logs" / "agentguard_audit.jsonl"
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


# Passive mode: evaluate and record everything, enforce nothing. In memory
# only — toggled through /api/proxy/passive-mode and reset on restart.
_passive_mode = False


def get_passive_mode() -> bool:
    return _passive_mode


def set_passive_mode(value: bool) -> None:
    global _passive_mode
    _passive_mode = value
