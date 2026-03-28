"""Runtime configuration helpers for the backend app."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback used when dependency is absent
    load_dotenv = None

_ENV_PATH = Path(__file__).resolve().parent / ".env"


def load_environment() -> None:
    if load_dotenv is not None:
        load_dotenv(dotenv_path=_ENV_PATH, override=False)
        return

    env_path = _ENV_PATH
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() == "true"


def resolve_jwt_secret() -> str:
    raw = os.environ.get("JWT_SECRET")
    secret = raw.strip() if isinstance(raw, str) else ""
    if secret:
        return secret
    raise RuntimeError("JWT_SECRET must be set")


def server_port(default: int = 3000) -> int:
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
