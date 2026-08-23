"""Launch browser agents behind their own AgentGuard proxies, in one command.

    python scripts/launch_agent.py --agent BrowserOS
    python scripts/launch_agent.py --agent BrowserOS MicrosoftEdge

Starts each agent's proxy if it is not already up, opens each browser pointed at
its own, and stops again the proxies it started once the browsers close. A proxy
already running, started from the Guard screen or another terminal, is used as
it is and left running.

The named agents are deliberately not configured through the operating system's
proxy dialog: a machine has one system proxy setting and `AllTraffic` already
uses it, so a named agent takes its endpoint on the command line instead. The
port comes from `ports_for_agent`, the same allocation the backend and the Guard
screen report, so it cannot drift from the catalogue.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.proxy.audit.agents import AGENT_CATALOGUE, normalize_proxy_agent_name
from backend.proxy.launcher import start_proxy_process, stop_proxy_process
from backend.proxy.launcher.browser import (
    BROWSER_PATHS,
    PROXY_HOST,
    build_command,
    find_browser,
    platform_key,
)
from backend.proxy.launcher.probe import port_is_listening
from backend.proxy.ports import UnknownAgentError, ports_for_agent

PROXY_READY_TIMEOUT = 15.0

def wait_for_port(port: int, timeout: float = PROXY_READY_TIMEOUT) -> bool:
    """Block until the proxy accepts connections, so the browser does not open
    before there is anything to open into."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_is_listening(port, PROXY_HOST):
            return True
        time.sleep(0.25)
    return False


def resolve(agent_names: list[str], browser_path: str | None) -> list[tuple[str, int, str]] | None:
    """Agent, port and executable for each name, or None if one cannot be met.

    Resolved for every agent before anything is started, so a missing browser
    is reported with nothing left running behind it.
    """
    resolved: list[tuple[str, int, str]] = []
    for agent in dict.fromkeys(normalize_proxy_agent_name(name) for name in agent_names):
        try:
            ports = ports_for_agent(agent)
        except UnknownAgentError as exc:
            print(f"{exc}. Known agents: {', '.join(AGENT_CATALOGUE)}", file=sys.stderr)
            return None
        browser = browser_path or find_browser(agent)
        if not browser:
            print(
                f"Could not find {agent} on this machine. Pass the executable with\n"
                f"  python scripts/launch_agent.py --agent {agent} --browser-path <path>",
                file=sys.stderr,
            )
            return None
        resolved.append((agent, ports.listen_port, browser))
    return resolved


def ensure_proxy(agent: str, port: int) -> bool | None:
    """Bring this agent's proxy up. True if we started it, None if it failed.

    False means it was already serving, and so is not ours to stop afterwards.
    """
    if port_is_listening(port, PROXY_HOST):
        return False
    ok, message = start_proxy_process(agent)
    if not ok:
        print(f"Could not start the proxy for {agent}: {message}", file=sys.stderr)
        return None
    if not wait_for_port(port):
        stop_proxy_process(agent)
        print(
            f"The proxy for {agent} did not come up on port {port} in "
            f"{PROXY_READY_TIMEOUT:.0f}s.",
            file=sys.stderr,
        )
        return None
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch browser agents behind their own AgentGuard proxies.",
    )
    parser.add_argument(
        "--agent",
        required=True,
        nargs="+",
        metavar="NAME",
        help="Which agents to launch: " + ", ".join(AGENT_CATALOGUE),
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
        help="Leave the proxies running after the browsers close.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the commands that would run, and start nothing.",
    )
    args, passthrough = parser.parse_known_args()

    if args.browser_path and len(set(args.agent)) > 1:
        parser.error("--browser-path names one executable, so it takes a single --agent")

    plans = resolve(args.agent, args.browser_path)
    if plans is None:
        return 1

    commands = [
        (agent, port, build_command(browser, port, agent, own_profile=not args.use_main_profile) + passthrough)
        for agent, port, browser in plans
    ]

    if args.dry_run:
        for _agent, _port, command in commands:
            print(" ".join(command))
        return 0

    # Every proxy first, so a failure to start one happens before any browser is
    # open and there is nothing to tear back down.
    started_here: list[str] = []
    try:
        for agent, port, _command in commands:
            started = ensure_proxy(agent, port)
            if started is None:
                return 1
            if started:
                started_here.append(agent)

        running: list[tuple[str, subprocess.Popen]] = []
        for agent, port, command in commands:
            print(f"Launching {agent} through {PROXY_HOST}:{port}")
            running.append((agent, subprocess.Popen(command)))

        exit_code = 0
        for agent, process in running:
            exit_code = process.wait() or exit_code
        return exit_code
    except KeyboardInterrupt:
        return 130
    finally:
        if not args.keep_proxy:
            for agent in started_here:
                stop_proxy_process(agent)
                print(f"Stopped the proxy for {agent}")


if __name__ == "__main__":
    raise SystemExit(main())
