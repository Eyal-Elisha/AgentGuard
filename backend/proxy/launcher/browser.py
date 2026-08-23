"""Finding an agent's browser and opening it behind that agent's proxy.

Only the agents listed here can be launched: All traffic is the machine's proxy
setting rather than an application.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from backend.proxy.ports import UnknownAgentError, ports_for_agent

from .command import spawn_kwargs

_logger = logging.getLogger(__name__)

PROXY_HOST = "127.0.0.1"

# First hit wins; a name without a separator is looked up on PATH.
BROWSER_PATHS: dict[str, dict[str, tuple[str, ...]]] = {
    "BrowserOS": {
        # It installs as a plain Chromium build, with nothing in the path
        # carrying its own name. Branded locations are probed first anyway.
        "win32": (
            r"%LOCALAPPDATA%\Programs\BrowserOS\BrowserOS.exe",
            r"%PROGRAMFILES%\BrowserOS\BrowserOS.exe",
            r"%LOCALAPPDATA%\Chromium\Application\chrome.exe",
            "browseros",
        ),
        "darwin": (
            "/Applications/BrowserOS.app/Contents/MacOS/BrowserOS",
            "~/Applications/BrowserOS.app/Contents/MacOS/BrowserOS",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "browseros",
        ),
        "linux": ("browseros", "browseros-stable", "chromium-browser", "chromium"),
    },
    "MicrosoftEdge": {
        "win32": (
            r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe",
            r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe",
            "msedge",
        ),
        "darwin": (
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "~/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "microsoft-edge",
        ),
        "linux": ("microsoft-edge", "microsoft-edge-stable"),
    },
}


def is_launchable(agent_name: str) -> bool:
    return agent_name in BROWSER_PATHS


def platform_key(platform: str | None = None) -> str:
    """Anything not Windows or macOS is treated as Linux, where browsers are
    found on PATH anyway."""
    current = platform if platform is not None else sys.platform
    if current == "win32":
        return "win32"
    if current == "darwin":
        return "darwin"
    return "linux"


def find_browser(agent: str, platform: str | None = None) -> str | None:
    """The executable for this agent, or None if no candidate exists here."""
    for candidate in BROWSER_PATHS.get(agent, {}).get(platform_key(platform), ()):
        expanded = os.path.expandvars(os.path.expanduser(candidate))
        if "/" in expanded or "\\" in expanded:
            if Path(expanded).is_file():
                return expanded
            continue
        discovered = shutil.which(expanded)
        if discovered:
            return discovered
    return None


def build_command(browser: str, port: int, agent: str, *, own_profile: bool) -> list[str]:
    command = [browser, f"--proxy-server={PROXY_HOST}:{port}"]
    if own_profile:
        # Chromium hands a launch to an instance that is already running, and
        # ignores --proxy-server when it does. A profile of its own forces a
        # new process.
        profile_dir = Path(tempfile.gettempdir()) / f"agentguard-{agent}"
        profile_dir.mkdir(parents=True, exist_ok=True)
        command.append(f"--user-data-dir={profile_dir}")
    return command


def launch_browser(agent_name: str) -> tuple[bool, str]:
    """Open this agent's browser pointed at its own proxy port.

    Never waited on: holding the request open until the operator closed the
    browser would hang the Guard screen. A failure is reported rather than
    raised, since the proxy is up either way.
    """
    if not is_launchable(agent_name):
        return False, "not_launchable"
    try:
        port = ports_for_agent(agent_name).listen_port
    except UnknownAgentError as exc:
        return False, str(exc)

    browser = find_browser(agent_name)
    if not browser:
        return False, f"Could not find {agent_name} on this machine."

    command = build_command(browser, port, agent_name, own_profile=True)
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            **spawn_kwargs(),
        )
    except OSError as exc:
        _logger.exception("Failed to launch %s", agent_name)
        return False, str(exc)
    return True, "launched"
