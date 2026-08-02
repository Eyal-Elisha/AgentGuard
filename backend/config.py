"""Runtime configuration helpers for the backend app."""

from __future__ import annotations

import os


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
