"""The per-agent launcher registry: one mitmweb instance per agent, addressed
by name, so starting or stopping one never touches another."""

from __future__ import annotations

import signal
import subprocess
from unittest.mock import patch

import pytest

from backend.proxy.launcher import (
    any_proxy_running,
    build_mitmweb_command,
    proxy_is_running,
    proxy_status_snapshot,
    start_proxy_process,
    stop_proxy_process,
)
from backend.proxy.launcher import command as launcher_command
from backend.proxy.launcher import registry as launcher_registry
from backend.proxy.launcher import termination as launcher_termination


class FakeProcess:
    """Stands in for a mitmweb Popen: alive until something terminates it."""

    def __init__(self, cmd, **kwargs):
        self.cmd = cmd
        self.kwargs = kwargs
        self.env = kwargs.get("env", {})
        self.pid = 4242
        self.returncode = None

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.returncode = 0
        return 0

    def kill(self):
        self.returncode = -9

    def terminate(self):
        self.returncode = 0


@pytest.fixture
def launcher(tmp_path):
    """A launcher with an empty registry, fake processes and no real kills."""
    spawned: list[FakeProcess] = []

    def fake_popen(cmd, **kwargs):
        process = FakeProcess(cmd, **kwargs)
        spawned.append(process)
        return process

    launcher_registry._instances.clear()
    with (
        patch.object(launcher_registry.subprocess, "Popen", side_effect=fake_popen),
        patch.object(launcher_termination.subprocess, "run"),
        patch.object(launcher_command, "_resolve_mitmweb_executable", return_value="mitmweb"),
        patch.object(launcher_registry, "kill_process_on_port", return_value=False) as kill_on_port,
        patch.object(launcher_registry.time, "sleep"),
        patch.object(launcher_command, "log_path_for", side_effect=lambda name: tmp_path / f"mitmweb-{name}.log"),
    ):
        yield type("Launcher", (), {"spawned": spawned, "kill_on_port": kill_on_port})
    launcher_registry._instances.clear()


def test_command_carries_both_allocated_ports(launcher):
    command = build_mitmweb_command("MicrosoftEdge")
    assert command[command.index("--listen-port") + 1] == "8082"
    assert command[command.index("--web-port") + 1] == "8182"


def test_administrative_port_is_never_left_to_mitmweb_default(launcher):
    """Left implicit, every instance would serve its interface on one port."""
    for agent_name in ("AllTraffic", "BrowserOS", "MicrosoftEdge"):
        assert "--web-port" in build_mitmweb_command(agent_name)


def test_several_agents_run_at_once_on_their_own_ports(launcher):
    for agent_name in ("AllTraffic", "BrowserOS", "MicrosoftEdge"):
        assert start_proxy_process(agent_name) == (True, "started")
        assert proxy_is_running(agent_name) is True

    listen_ports = [
        process.cmd[process.cmd.index("--listen-port") + 1] for process in launcher.spawned
    ]
    assert listen_ports == ["8080", "8081", "8082"]


def test_stopping_one_agent_leaves_the_others_running(launcher):
    for agent_name in ("AllTraffic", "BrowserOS", "MicrosoftEdge"):
        start_proxy_process(agent_name)

    assert stop_proxy_process("BrowserOS") == (True, "stopped")

    assert proxy_is_running("BrowserOS") is False
    assert proxy_is_running("AllTraffic") is True
    assert proxy_is_running("MicrosoftEdge") is True
    assert any_proxy_running() is True


def test_each_agent_writes_its_own_log(launcher, tmp_path):
    start_proxy_process("BrowserOS")
    start_proxy_process("MicrosoftEdge")
    stop_proxy_process("BrowserOS")
    stop_proxy_process("MicrosoftEdge")

    browseros_log = (tmp_path / "mitmweb-BrowserOS.log").read_text(encoding="utf-8")
    edge_log = (tmp_path / "mitmweb-MicrosoftEdge.log").read_text(encoding="utf-8")
    assert "--listen-port 8081" in browseros_log
    assert "--listen-port 8081" not in edge_log
    assert "--listen-port 8082" in edge_log


def test_agent_identity_and_environment_travel_to_the_process(launcher):
    start_proxy_process("MicrosoftEdge", environment="test")
    env = launcher.spawned[0].env
    assert env["AGENTGUARD_PROXY_AGENT_NAME"] == "MicrosoftEdge"
    assert env["AGENTGUARD_PROXY_ENVIRONMENT"] == "test"


def test_starting_an_already_running_agent_does_not_spawn_a_second(launcher):
    start_proxy_process("BrowserOS")
    assert start_proxy_process("BrowserOS") == (True, "already_running")
    assert len(launcher.spawned) == 1


def test_start_is_idempotent_per_agent_not_globally(launcher):
    """A running BrowserOS must not make MicrosoftEdge look already started."""
    start_proxy_process("BrowserOS")
    assert start_proxy_process("MicrosoftEdge") == (True, "started")
    assert len(launcher.spawned) == 2


def test_stop_falls_back_to_the_port_of_the_agent_being_stopped(launcher):
    """With no registry entry (started outside Flask), the fallback kill has to
    target this agent's port, or it would take down a different agent."""
    assert stop_proxy_process("MicrosoftEdge") == (True, "not_running")
    launcher.kill_on_port.assert_called_once_with(8082)


def test_stop_reports_stopped_when_the_fallback_kills_something(launcher):
    launcher.kill_on_port.return_value = True
    assert stop_proxy_process("AllTraffic") == (True, "stopped")
    launcher.kill_on_port.assert_called_once_with(8080)


def test_an_agent_whose_process_died_is_forgotten(launcher):
    start_proxy_process("BrowserOS")
    launcher.spawned[0].returncode = 1
    assert proxy_is_running("BrowserOS") is False
    assert any_proxy_running() is False


def test_status_reports_every_agent_with_its_endpoint(launcher):
    start_proxy_process("MicrosoftEdge", environment="test")

    snapshot = {entry["agent_name"]: entry for entry in proxy_status_snapshot()}
    assert list(snapshot) == ["AllTraffic", "BrowserOS", "MicrosoftEdge"]

    assert snapshot["MicrosoftEdge"]["active"] is True
    assert snapshot["MicrosoftEdge"]["proxy_port"] == 8082
    assert snapshot["MicrosoftEdge"]["admin_port"] == 8182
    assert snapshot["MicrosoftEdge"]["environment"] == "test"

    # Reported even when idle: the endpoint is what the operator needs first.
    assert snapshot["AllTraffic"]["active"] is False
    assert snapshot["AllTraffic"]["proxy_port"] == 8080
    assert snapshot["AllTraffic"]["environment"] is None


def test_posix_instances_get_their_own_process_group(launcher):
    with patch.object(launcher_command.sys, "platform", "darwin"):
        start_proxy_process("BrowserOS")
    assert launcher.spawned[0].kwargs.get("start_new_session") is True


def test_posix_stop_signals_the_whole_group_not_just_the_parent(launcher):
    """mitmweb's workers hold the listen port, so the parent alone leaves it
    taken and the agent cannot be started again."""
    start_proxy_process("BrowserOS")
    with (
        patch.object(launcher_termination.sys, "platform", "darwin"),
        patch.object(launcher_termination.os, "getpgid", return_value=4242, create=True),
        patch.object(launcher_termination.os, "killpg", create=True) as killpg,
    ):
        assert stop_proxy_process("BrowserOS") == (True, "stopped")

    killpg.assert_called_once_with(4242, signal.SIGTERM)


def test_windows_instances_are_not_put_in_a_process_group(launcher):
    """start_new_session is POSIX-only; Windows kills the tree with taskkill."""
    with patch.object(launcher_command.sys, "platform", "win32"):
        start_proxy_process("BrowserOS")
    assert "start_new_session" not in launcher.spawned[0].kwargs


def test_a_kill_that_times_out_is_reported_rather_than_raised(launcher):
    """taskkill and wait raise TimeoutExpired, which is not an OSError, so a
    kill that hung used to reach the route as an unhandled exception."""
    start_proxy_process("BrowserOS")

    with patch.object(
        launcher_registry,
        "terminate",
        side_effect=subprocess.TimeoutExpired(cmd="taskkill", timeout=10),
    ):
        ok, message = stop_proxy_process("BrowserOS")

    assert ok is False
    assert "taskkill" in message
    # The entry is dropped either way, so a retry takes the port-based fallback
    # rather than trusting a handle we could not kill.
    assert proxy_is_running("BrowserOS") is False


def test_an_agent_with_no_allocation_cannot_be_started(launcher):
    ok, message = start_proxy_process("Firefox")
    assert ok is False
    assert "no port allocated" in message
    assert launcher.spawned == []
