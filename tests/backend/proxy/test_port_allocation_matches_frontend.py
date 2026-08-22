"""The dashboard works out the port allocation itself, so it can show an
endpoint before that agent's proxy is running. These read the JavaScript and
check it still agrees with ports_for_agent."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from backend.proxy.audit.agents import AGENT_CATALOGUE
from backend.proxy.ports import ports_for_agent

AGENT_OPTIONS_JS = (
    Path(__file__).resolve().parents[3] / "frontend" / "src" / "constants" / "agentOptions.js"
)


@pytest.fixture(scope="module")
def source() -> str:
    if not AGENT_OPTIONS_JS.is_file():
        pytest.skip(f"{AGENT_OPTIONS_JS} is not present")
    return AGENT_OPTIONS_JS.read_text(encoding="utf-8")


def _const(source: str, name: str) -> int:
    match = re.search(rf"^const {name} = (\d+);$", source, re.MULTILINE)
    assert match, f"{name} is not declared in agentOptions.js"
    return int(match.group(1))


def _agent_options(source: str) -> list[str]:
    match = re.search(r"export const AGENT_OPTIONS = (\[[^\]]*\]);", source)
    assert match, "AGENT_OPTIONS is not declared in agentOptions.js"
    return json.loads(match.group(1).replace("'", '"'))


def test_the_catalogue_order_is_the_same_on_both_sides(source):
    """Ports come from a position in this list, so its order is load-bearing."""
    assert _agent_options(source) == list(AGENT_CATALOGUE)


def test_every_agent_lands_on_the_port_the_backend_allocates(source):
    listen_base = _const(source, "LISTEN_BASE")
    admin_base = _const(source, "ADMIN_BASE")

    for offset, agent in enumerate(_agent_options(source)):
        ports = ports_for_agent(agent)
        assert listen_base + offset == ports.listen_port, agent
        assert admin_base + offset == ports.web_port, agent
