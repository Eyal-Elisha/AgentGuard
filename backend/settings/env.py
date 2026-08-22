"""Reading `backend/.env` and the primitives the other settings modules share."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

_logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

_loaded = False


def load_settings_env() -> None:
    """Populate unset process env vars from `backend/.env`, exactly once.

    Called by every getter below rather than at import time, because the proxy
    addon and the Flask app start as separate processes and neither can assume
    the other has run.
    """
    global _loaded
    if _loaded:
        return
    load_dotenv(BACKEND_DIR / ".env", override=False)
    _loaded = True


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() == "true"


def read_env(name: str) -> str:
    """The named variable, stripped, after loading `.env`. Empty when unset."""
    load_settings_env()
    return (os.getenv(name) or "").strip()


def read_port(raw: str, *, env_name: str, default_port: int) -> int:
    """A TCP port from `raw`, warning and falling back when it is unusable."""
    if not raw:
        return default_port
    try:
        port = int(raw)
    except ValueError:
        _logger.warning("[AgentGuard] Invalid %s=%r; falling back to %s", env_name, raw, default_port)
        return default_port
    if not (1 <= port <= 65535):
        _logger.warning("[AgentGuard] Out-of-range %s=%r; falling back to %s", env_name, raw, default_port)
        return default_port
    return port
