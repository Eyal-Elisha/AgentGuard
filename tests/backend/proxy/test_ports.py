"""Deterministic per-agent port allocation."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from backend.proxy.audit.agents import AGENT_CATALOGUE, DEFAULT_AGENT_NAME
from backend.proxy.ports import UnknownAgentError, all_agent_ports, ports_for_agent


def test_default_agent_keeps_the_unchanged_interception_port():
    """The catch-all is the default, and keeps the port the proxy has always
    listened on, since that is the one already in machine-wide proxy settings."""
    assert DEFAULT_AGENT_NAME == "AllTraffic"
    ports = ports_for_agent(DEFAULT_AGENT_NAME)
    assert (ports.listen_port, ports.web_port) == (8080, 8180)


def test_later_catalogue_agents_take_the_next_slots_in_both_ranges():
    browseros = ports_for_agent("BrowserOS")
    edge = ports_for_agent("MicrosoftEdge")
    assert (browseros.listen_port, browseros.web_port) == (8081, 8181)
    assert (edge.listen_port, edge.web_port) == (8082, 8182)


def test_nth_agent_is_offset_by_its_catalogue_position():
    assert len(AGENT_CATALOGUE) >= 3
    for offset, agent_name in enumerate(AGENT_CATALOGUE):
        ports = ports_for_agent(agent_name)
        assert ports.listen_port == 8080 + offset
        assert ports.web_port == 8180 + offset


def test_no_interception_port_collides_with_an_administrative_port():
    """The collision the separate bases exist to avoid."""
    listen_ports = {ports.listen_port for ports in all_agent_ports()}
    web_ports = {ports.web_port for ports in all_agent_ports()}
    assert listen_ports.isdisjoint(web_ports)


def test_allocation_is_stable_across_calls():
    assert ports_for_agent("MicrosoftEdge") == ports_for_agent("MicrosoftEdge")


def test_name_is_canonicalised_before_allocation():
    """An alias and a case variant land on the same slot as the canonical name."""
    canonical = ports_for_agent("MicrosoftEdge")
    assert ports_for_agent("gemini") == canonical
    assert ports_for_agent("microsoftedge") == canonical
    assert ports_for_agent("All traffic") == ports_for_agent("AllTraffic")


def test_missing_agent_falls_back_to_the_default_agent():
    assert ports_for_agent(None) == ports_for_agent(DEFAULT_AGENT_NAME)


def test_agent_outside_the_catalogue_has_no_allocation():
    with pytest.raises(UnknownAgentError):
        ports_for_agent("Firefox")


def test_bases_follow_their_environment_variables():
    with patch.dict(os.environ, {"PROXY_PORT": "9000", "PROXY_WEB_PORT": "9500"}, clear=False):
        ports = ports_for_agent("MicrosoftEdge")
    assert (ports.listen_port, ports.web_port) == (9002, 9502)


def test_overlapping_bases_fall_back_to_the_defaults():
    """Bases a single port apart put the second agent's interception port on the
    first agent's administrative port, so they are rejected together."""
    with patch.dict(os.environ, {"PROXY_PORT": "8080", "PROXY_WEB_PORT": "8081"}, clear=False):
        ports = ports_for_agent("MicrosoftEdge")
    assert (ports.listen_port, ports.web_port) == (8082, 8182)
