"""Which two ports each agent's proxy instance owns.

Allocation is deterministic rather than dynamic: nothing hands the endpoint to
the agent, the operator types it in by hand, so an agent has to land on the
same port every run. Each takes its offset from its place in `AGENT_CATALOGUE`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.settings import (
    DEFAULT_PROXY_PORT,
    DEFAULT_PROXY_WEB_PORT,
    get_proxy_port,
    get_proxy_web_port,
)

from .audit.agents import AGENT_CATALOGUE, normalize_proxy_agent_name

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentPorts:
    """The port an agent is pointed at, and the one mitmweb serves its own UI on."""

    agent_name: str
    listen_port: int
    web_port: int


class UnknownAgentError(ValueError):
    """Raised for an agent with no slot in the catalogue, and so no ports."""


def ports_for_agent(agent_name: str | None) -> AgentPorts:
    """The ports allocated to `agent_name`, by its position in the catalogue."""
    agent = normalize_proxy_agent_name(agent_name)
    try:
        offset = AGENT_CATALOGUE.index(agent)
    except ValueError:
        raise UnknownAgentError(
            f"{agent!r} is not a known agent, so it has no port allocated to it"
        ) from None
    listen_base, web_base = _bases()
    return AgentPorts(
        agent_name=agent,
        listen_port=listen_base + offset,
        web_port=web_base + offset,
    )


def all_agent_ports() -> list[AgentPorts]:
    """Every catalogue agent's allocation, in catalogue order."""
    return [ports_for_agent(name) for name in AGENT_CATALOGUE]


def _bases() -> tuple[int, int]:
    """The interception and administrative bases, refused if they would overlap.

    mitmweb serves its administrative interface on the port immediately above
    its interception port, so the ranges need enough room between them for one
    catalogue. Too close, and the second agent's interception port is the first
    agent's administrative port, which surfaces only as an agent that will not
    start.
    """
    listen_base = get_proxy_port()
    web_base = get_proxy_web_port()
    if abs(web_base - listen_base) >= len(AGENT_CATALOGUE):
        return listen_base, web_base
    _logger.warning(
        "[AgentGuard] PROXY_PORT=%s and PROXY_WEB_PORT=%s leave less than %s between them, "
        "so the port ranges would overlap; falling back to %s and %s",
        listen_base,
        web_base,
        len(AGENT_CATALOGUE),
        DEFAULT_PROXY_PORT,
        DEFAULT_PROXY_WEB_PORT,
    )
    return DEFAULT_PROXY_PORT, DEFAULT_PROXY_WEB_PORT
