"""How to invoke mitmweb for one agent, and where its output goes."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import IO

from backend.proxy.ports import ports_for_agent
from backend.settings import load_settings_env

DEFAULT_ENVIRONMENT = "prod"


def repo_root() -> Path:
    """The repository root, which is what the proxy runs from."""
    return Path(__file__).resolve().parents[3]


def _resolve_mitmweb_executable() -> str:
    sibling_name = "mitmweb.exe" if sys.platform.startswith("win") else "mitmweb"
    sibling = Path(sys.executable).resolve().with_name(sibling_name)
    if sibling.is_file():
        return str(sibling)
    discovered = shutil.which("mitmweb")
    if discovered:
        return discovered
    raise RuntimeError("Could not find mitmweb in the current environment.")


def build_mitmweb_command(agent_name: str | None = None) -> list[str]:
    """The argv for this agent's instance (excluding CLI passthrough).

    The administrative port is passed explicitly rather than left to mitmweb's
    default, which would put every instance's own interface on one port.
    """
    load_settings_env()
    ports = ports_for_agent(agent_name)
    script_path = repo_root() / "backend" / "proxy" / "traffic_interception.py"
    return [
        _resolve_mitmweb_executable(),
        "-s",
        str(script_path),
        "--listen-port",
        str(ports.listen_port),
        "--web-port",
        str(ports.web_port),
        "--no-web-open-browser",
    ]


def mitm_env(agent_name: str, environment: str) -> dict[str, str]:
    env = os.environ.copy()
    # TODO: Remove this once the project is packaged/installable and mitm can import `backend` without PYTHONPATH.
    env["PYTHONPATH"] = str(repo_root())
    # The agent's identity travels to the proxy here, so every decision the
    # instance reports is attributed without the request having to say so.
    env["AGENTGUARD_PROXY_AGENT_NAME"] = agent_name
    env["AGENTGUARD_PROXY_ENVIRONMENT"] = environment
    return env


def log_path_for(agent_name: str) -> Path:
    """One log per agent: a shared file written by two instances interleaves."""
    log_dir = repo_root() / ".agentguard"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"mitmweb-{agent_name}.log"


def open_log(agent_name: str, environment: str, cmd: list[str]) -> IO[str]:
    """Open this agent's log and write the header for a new run.

    Raises OSError, which the caller reports rather than starting blind.
    """
    handle = open(log_path_for(agent_name), "a", encoding="utf-8", buffering=1)
    handle.write(
        f"\n--- mitmweb start {time.strftime('%Y-%m-%d %H:%M:%S')} "
        f"agent={agent_name} environment={environment} ---\n"
    )
    handle.write("cmd: " + " ".join(cmd) + "\n")
    return handle


def close_log(handle: IO[str] | None, note: str) -> None:
    """Write a closing note and close, ignoring a log that is already broken."""
    if handle is None:
        return
    try:
        handle.write(f"{note}\n")
        handle.flush()
        handle.close()
    except OSError:
        pass


def spawn_kwargs() -> dict:
    """Platform-specific Popen options for an instance.

    Paired deliberately with `termination.terminate`: off Windows the instance
    gets its own session precisely so stopping it can signal the whole group.
    """
    if sys.platform == "win32":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {"start_new_session": True}
