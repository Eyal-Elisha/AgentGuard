"""Canonical names for the browser agents AgentGuard sits in front of. The name
arrives as untrusted text, so it is stripped, length-capped and mapped onto a
name the UI knows.
"""

from __future__ import annotations

DEFAULT_AGENT_NAME = "BrowserOS"

_CANONICAL_NAMES = ("MicrosoftEdge", "BrowserOS")

# Renamed agents only — keep in sync with LEGACY_AGENT_KEYS in
# frontend/src/constants/agentOptions.js
_LEGACY_ALIASES = {
    "gemini": "MicrosoftEdge",
}

_ALLOWED_PUNCTUATION = "._ -"
_MAX_LENGTH = 20


def normalize_proxy_agent_name(explicit_agent_name: str | None) -> str:
    """Return the canonical agent name, falling back to the default."""
    if not isinstance(explicit_agent_name, str) or not explicit_agent_name.strip():
        return DEFAULT_AGENT_NAME
    return _to_canonical(_clean(explicit_agent_name))


def _clean(value: str) -> str:
    cleaned = "".join(
        ch for ch in value.strip() if ch.isalnum() or ch in _ALLOWED_PUNCTUATION
    )
    if not cleaned:
        return DEFAULT_AGENT_NAME
    return cleaned[:_MAX_LENGTH]


def _to_canonical(cleaned: str) -> str:
    lower = cleaned.lower()
    legacy = _LEGACY_ALIASES.get(lower)
    if legacy:
        return legacy
    for name in _CANONICAL_NAMES:
        if name.lower() == lower:
            return name
    return cleaned
