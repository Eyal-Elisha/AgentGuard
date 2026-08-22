"""Run one AgentGuard proxy instance in the foreground.

The command-line face of `backend/proxy/launcher/`, which the dashboard drives
through `backend/routes/proxy_control.py` instead.
"""

from __future__ import annotations

import argparse
import subprocess

from backend.proxy.audit.agents import AGENT_CATALOGUE, normalize_proxy_agent_name
from backend.proxy.launcher import (
    DEFAULT_ENVIRONMENT,
    build_mitmweb_command,
    mitm_env,
    repo_root,
)
from backend.proxy.ports import UnknownAgentError
from backend.settings import load_settings_env


def main() -> int:
    load_settings_env()
    parser = argparse.ArgumentParser(
        description="Run one AgentGuard proxy instance in the foreground.",
    )
    parser.add_argument(
        "--agent",
        default=None,
        metavar="NAME",
        help=(
            "Which agent's allocated ports to listen on: "
            + ", ".join(AGENT_CATALOGUE)
            + f" (default: {AGENT_CATALOGUE[0]})"
        ),
    )
    parser.add_argument(
        "--environment",
        default=DEFAULT_ENVIRONMENT,
        help=f"Environment label recorded against the session (default: {DEFAULT_ENVIRONMENT})",
    )
    args, passthrough = parser.parse_known_args()

    agent = normalize_proxy_agent_name(args.agent)
    try:
        command = build_mitmweb_command(agent)
    except UnknownAgentError as exc:
        parser.error(str(exc))
    command.extend(passthrough)
    return subprocess.call(
        command,
        cwd=repo_root(),
        env=mitm_env(agent, args.environment),
    )


if __name__ == "__main__":
    raise SystemExit(main())
