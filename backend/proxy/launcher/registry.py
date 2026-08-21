"""What is running, keyed by agent.

One entry per live instance, so start, stop and status each address exactly one
and leave the others alone.
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from typing import IO, Any

from backend.proxy.audit.agents import AGENT_CATALOGUE, normalize_proxy_agent_name
from backend.proxy.ports import AgentPorts, UnknownAgentError, ports_for_agent

from .command import (
    DEFAULT_ENVIRONMENT,
    build_mitmweb_command,
    close_log,
    log_path_for,
    mitm_env,
    open_log,
    repo_root,
    spawn_kwargs,
)
from .termination import kill_process_on_port, terminate

_logger = logging.getLogger(__name__)


@dataclass
class Instance:
    """One running proxy, and everything needed to address it again."""

    agent_name: str
    environment: str
    ports: AgentPorts
    process: subprocess.Popen
    log_handle: IO[str] | None


# Keyed by canonical agent name, so start, stop and status address one entry.
_instances: dict[str, Instance] = {}


def _live_instance(agent_name: str) -> Instance | None:
    """The entry for this agent, dropped if its process has exited."""
    instance = _instances.get(agent_name)
    if instance is None:
        return None
    if instance.process.poll() is not None:
        _forget(instance, "--- mitmweb already stopped ---")
        return None
    return instance


def _forget(instance: Instance, closing_note: str) -> None:
    close_log(instance.log_handle, closing_note)
    instance.log_handle = None
    _instances.pop(instance.agent_name, None)


def proxy_is_running(agent_name: str | None = None) -> bool:
    """Whether this agent's instance is running. Defaults to the default agent."""
    return _live_instance(normalize_proxy_agent_name(agent_name)) is not None


def any_proxy_running() -> bool:
    """Whether any agent is currently protected."""
    return any(_live_instance(name) is not None for name in list(_instances))


def proxy_status_snapshot() -> list[dict[str, Any]]:
    """One entry per catalogue agent: its allocation and whether it is running.

    Reports every agent rather than only the running ones, because the endpoint
    is what the operator needs before starting anything.
    """
    snapshot: list[dict[str, Any]] = []
    for agent_name in AGENT_CATALOGUE:
        instance = _live_instance(agent_name)
        ports = instance.ports if instance is not None else ports_for_agent(agent_name)
        snapshot.append(
            {
                "agent_name": agent_name,
                "active": instance is not None,
                "proxy_port": ports.listen_port,
                "admin_port": ports.web_port,
                "environment": instance.environment if instance is not None else None,
            }
        )
    return snapshot


def start_proxy_process(
    agent_name: str | None = None,
    environment: str = DEFAULT_ENVIRONMENT,
) -> tuple[bool, str]:
    """Start this agent's mitmweb with `traffic_interception.py` (decision
    enforcement). Idempotent per agent, and leaves every other agent alone."""
    agent = normalize_proxy_agent_name(agent_name)
    if _live_instance(agent) is not None:
        return True, "already_running"
    try:
        ports = ports_for_agent(agent)
        cmd = build_mitmweb_command(agent)
    except (UnknownAgentError, RuntimeError) as exc:
        return False, str(exc)
    try:
        log_handle = open_log(agent, environment, cmd)
    except OSError as exc:
        return False, f"Failed to open mitmweb log file: {exc}"

    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(repo_root()),
            env=mitm_env(agent, environment),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            **spawn_kwargs(),
        )
    except OSError as exc:
        _logger.exception("Failed to start mitmweb for %s", agent)
        close_log(log_handle, f"Failed to spawn mitmweb: {exc}")
        return False, str(exc)

    _instances[agent] = Instance(
        agent_name=agent,
        environment=environment,
        ports=ports,
        process=process,
        log_handle=log_handle,
    )

    # Give mitmweb a moment to fail fast (missing executable, port in use, bad addon import, etc.)
    time.sleep(0.35)
    if _live_instance(agent) is None:
        exit_code = process.poll()
        close_log(log_handle, f"mitmweb exited early (exit_code={exit_code}).")
        _instances.pop(agent, None)
        return False, (
            f"mitmweb for {agent} exited early (exit_code={exit_code}). "
            f"See {log_path_for(agent)} for details."
        )

    return True, "started"


def stop_proxy_process(agent_name: str | None = None) -> tuple[bool, str]:
    """Terminate this agent's instance, leaving every other agent running.

    If the agent has no entry (its proxy was started externally), falls back to
    killing whatever is listening on the port allocated to *this* agent.
    """
    agent = normalize_proxy_agent_name(agent_name)
    instance = _live_instance(agent)
    if instance is None:
        try:
            fallback_port = ports_for_agent(agent).listen_port
        except UnknownAgentError as exc:
            return False, str(exc)
        killed = kill_process_on_port(fallback_port)
        return True, "stopped" if killed else "not_running"

    try:
        terminate(instance.process)
    except (OSError, subprocess.SubprocessError) as exc:
        _logger.exception("Failed to stop mitmweb for %s", agent)
        _forget(instance, f"Failed to stop mitmweb: {exc}")
        return False, str(exc)

    _forget(instance, "--- mitmweb stopped ---")
    return True, "stopped"
