"""An instance outliving the backend that started it.

mitmweb is spawned detached, so restarting the backend empties the registry
while every proxy it started keeps running and keeps its port. Status read from
the registry alone then reports those agents as off, and starting one again
fails to bind. These cover the port fallback that closes that gap.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.proxy.launcher import (
    any_proxy_running,
    proxy_is_running,
    proxy_status_snapshot,
    start_proxy_process,
)
from backend.proxy.launcher import registry as launcher_registry
from backend.proxy.ports import ports_for_agent


@pytest.fixture
def empty_registry():
    """A registry with no entries, as it is just after a backend restart."""
    with patch.dict(launcher_registry._instances, {}, clear=True):
        yield


@pytest.fixture
def listening():
    """Report only the named ports as served."""
    served: set[int] = set()

    def fake(port, *args, **kwargs):
        return port in served

    with patch.object(launcher_registry, "port_is_listening", side_effect=fake):
        yield served


def test_an_agent_still_serving_its_port_is_reported_as_protected(empty_registry, listening):
    listening.add(ports_for_agent("MicrosoftEdge").listen_port)

    assert proxy_is_running("MicrosoftEdge") is True
    assert any_proxy_running() is True


def test_an_agent_serving_nothing_is_reported_as_off(empty_registry, listening):
    assert proxy_is_running("MicrosoftEdge") is False
    assert any_proxy_running() is False


def test_only_the_agent_whose_port_is_served_is_reported(empty_registry, listening):
    """The bug this fixes showed one agent as off while its neighbour was on,
    so a fallback that answered for the whole catalogue would hide it again."""
    listening.add(ports_for_agent("BrowserOS").listen_port)

    by_name = {entry["agent_name"]: entry for entry in proxy_status_snapshot()}
    assert by_name["BrowserOS"]["active"] is True
    assert by_name["MicrosoftEdge"]["active"] is False
    assert by_name["AllTraffic"]["active"] is False


def test_the_snapshot_still_reports_every_agents_ports(empty_registry, listening):
    for entry in proxy_status_snapshot():
        ports = ports_for_agent(entry["agent_name"])
        assert entry["proxy_port"] == ports.listen_port
        assert entry["admin_port"] == ports.web_port


def test_starting_an_agent_that_is_already_serving_does_not_spawn_a_second(
    empty_registry, listening
):
    """A second instance would only fail to bind, and reporting that as an
    error told the operator their running proxy had failed to start."""
    listening.add(ports_for_agent("MicrosoftEdge").listen_port)

    with patch.object(launcher_registry.subprocess, "Popen") as popen:
        ok, message = start_proxy_process("MicrosoftEdge")

    assert (ok, message) == (True, "already_running")
    popen.assert_not_called()
