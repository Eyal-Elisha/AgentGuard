"""Canonical names for the agents AgentGuard sits in front of. The name arrives
as untrusted text, so it is stripped, length-capped and mapped onto a name the
UI knows.

The catalogue is ordered, and the order is load-bearing: `proxy/ports.py`
allocates each agent's ports from its position here, so appending is safe and
reordering moves every endpoint the operator has already configured.
"""

from __future__ import annotations

#: Every agent AgentGuard can launch a proxy instance for, in catalogue order.
#: `AllTraffic` is first and is the default: it is not tied to a named agent but
#: intercepts whatever is pointed at it, which is what the system proxy does.
#: It therefore keeps the port the proxy has always listened on.
AGENT_CATALOGUE = ("AllTraffic", "BrowserOS", "MicrosoftEdge")

DEFAULT_AGENT_NAME = AGENT_CATALOGUE[0]

# Spellings that are not the canonical name: renames, and the spaced and
# hyphenated forms of the display label. Keep in sync with AGENT_ALIASES in
# frontend/src/constants/agentOptions.js
_ALIASES = {
    "gemini": "MicrosoftEdge",
    "all traffic": "AllTraffic",
    "all-traffic": "AllTraffic",
    "all_traffic": "AllTraffic",
}

_ALLOWED_PUNCTUATION = "._ -"
_MAX_LENGTH = 20


def normalize_proxy_agent_name(explicit_agent_name: str | None) -> str:
    """Return the canonical agent name, falling back to the default."""
    if not isinstance(explicit_agent_name, str) or not explicit_agent_name.strip():
        return DEFAULT_AGENT_NAME
    return _to_canonical(_clean(explicit_agent_name))


def is_catalogue_agent(agent_name: str | None) -> bool:
    """Whether this name is one AgentGuard can allocate ports for and launch.

    A decision may be *recorded* against any name the proxy reports, but only a
    catalogue member has a port of its own, so only a catalogue member can be
    started.
    """
    return normalize_proxy_agent_name(agent_name) in AGENT_CATALOGUE


def _clean(value: str) -> str:
    cleaned = "".join(
        ch for ch in value.strip() if ch.isalnum() or ch in _ALLOWED_PUNCTUATION
    )
    if not cleaned:
        return DEFAULT_AGENT_NAME
    return cleaned[:_MAX_LENGTH]


def _to_canonical(cleaned: str) -> str:
    lower = cleaned.lower()
    alias = _ALIASES.get(lower)
    if alias:
        return alias
    for name in AGENT_CATALOGUE:
        if name.lower() == lower:
            return name
    return cleaned
