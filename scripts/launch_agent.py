"""Launch a browser agent behind its own AgentGuard proxy, in one command.

    python scripts/launch_agent.py --agent BrowserOS
    python scripts/launch_agent.py --agent MicrosoftEdge

Starts that agent's proxy if it is not already up, opens the browser pointed at
it, and stops the proxy again when the browser closes. A proxy already running,
started from the Guard screen or another terminal, is used as it is and left
running.

The named agents are deliberately not configured through the operating system's
proxy dialog: a machine has one system proxy setting and `AllTraffic` already
uses it, so a named agent takes its endpoint on the command line instead. The
port comes from `ports_for_agent`, the same allocation the backend and the Guard
screen report, so it cannot drift from the catalogue.
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.proxy.audit.agents import AGENT_CATALOGUE, normalize_proxy_agent_name
from backend.proxy.launcher import start_proxy_process, stop_proxy_process
from backend.proxy.ports import UnknownAgentError, ports_for_agent

PROXY_HOST = "127.0.0.1"
PROXY_READY_TIMEOUT = 15.0

# Where each agent is normally installed, by platform. First hit wins; a name
# without a separator is looked up on PATH. Override with --browser-path.
_BROWSER_PATHS: dict[str, dict[str, tuple[str, ...]]] = {
    "BrowserOS": {
        # BrowserOS ships as a Chromium build and installs under a plain
        # "Chromium" directory, with nothing in the path carrying its own name.
        # The branded locations are probed first in case a release moves there.
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


def platform_key(platform: str | None = None) -> str:
    """Which set of candidate paths applies. Anything not Windows or macOS is
    treated as Linux, where browsers are found on PATH anyway."""
    current = platform if platform is not None else sys.platform
    if current == "win32":
        return "win32"
    if current == "darwin":
        return "darwin"
    return "linux"


def find_browser(agent: str, platform: str | None = None) -> str | None:
    """The executable for this agent, or None if no candidate exists here."""
    for candidate in _BROWSER_PATHS.get(agent, {}).get(platform_key(platform), ()):
        expanded = os.path.expandvars(os.path.expanduser(candidate))
        if "/" in expanded or "\\" in expanded:
            if Path(expanded).is_file():
                return expanded
            continue
        discovered = shutil.which(expanded)
        if discovered:
            return discovered
    return None


def port_is_open(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.5)
        try:
            probe.connect((PROXY_HOST, port))
            return True
        except OSError:
            return False


def wait_for_port(port: int, timeout: float = PROXY_READY_TIMEOUT) -> bool:
    """Block until the proxy accepts connections, so the browser does not open
    before there is anything to open into."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_is_open(port):
            return True
        time.sleep(0.25)
    return False


def build_command(browser: str, port: int, agent: str, *, own_profile: bool) -> list[str]:
    command = [browser, f"--proxy-server={PROXY_HOST}:{port}"]
    if own_profile:
        # A profile of its own, so this launch is a new process that honours the
        # flag. Chromium hands a launch to an instance that is already running
        # and ignores --proxy-server when it does.
        profile_dir = Path(tempfile.gettempdir()) / f"agentguard-{agent}"
        profile_dir.mkdir(parents=True, exist_ok=True)
        command.append(f"--user-data-dir={profile_dir}")
    return command


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch a browser agent behind its own AgentGuard proxy.",
    )
    parser.add_argument(
        "--agent",
        required=True,
        metavar="NAME",
        help="Which agent to launch: " + ", ".join(AGENT_CATALOGUE),
    )
    parser.add_argument(
        "--browser-path",
        default=None,
        help="The browser executable, when it is not where this script looks.",
    )
    parser.add_argument(
        "--use-main-profile",
        action="store_true",
        help=(
            "Use your normal profile instead of a separate one. The browser must "
            "be fully quit first, or it will ignore the proxy setting."
        ),
    )
    parser.add_argument(
        "--keep-proxy",
        action="store_true",
        help="Leave the proxy running after the browser closes.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command that would run, and start nothing.",
    )
    args, passthrough = parser.parse_known_args()

    agent = normalize_proxy_agent_name(args.agent)
    try:
        ports = ports_for_agent(agent)
    except UnknownAgentError as exc:
        parser.error(f"{exc}. Known agents: {', '.join(AGENT_CATALOGUE)}")

    browser = args.browser_path or find_browser(agent)
    if not browser:
        print(
            f"Could not find {agent} on this machine. Pass the executable with\n"
            f"  python scripts/launch_agent.py --agent {agent} --browser-path <path>",
            file=sys.stderr,
        )
        return 1

    port = ports.listen_port
    command = build_command(browser, port, agent, own_profile=not args.use_main_profile)
    command.extend(passthrough)

    if args.dry_run:
        print(" ".join(command))
        return 0

    # A proxy someone else started is not ours to stop afterwards.
    started_here = False
    if not port_is_open(port):
        ok, message = start_proxy_process(agent)
        if not ok:
            print(f"Could not start the proxy for {agent}: {message}", file=sys.stderr)
            return 1
        started_here = True
        if not wait_for_port(port):
            stop_proxy_process(agent)
            print(
                f"The proxy for {agent} did not come up on port {port} in "
                f"{PROXY_READY_TIMEOUT:.0f}s.",
                file=sys.stderr,
            )
            return 1

    print(f"Launching {agent} through {PROXY_HOST}:{port}")
    try:
        return subprocess.call(command)
    except KeyboardInterrupt:
        return 130
    finally:
        if started_here and not args.keep_proxy:
            stop_proxy_process(agent)
            print(f"Stopped the proxy for {agent}")


if __name__ == "__main__":
    raise SystemExit(main())
