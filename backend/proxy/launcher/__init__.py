"""Starts, stops and reports on one mitmweb instance per agent.

Keyed by agent throughout, so acting on one never disturbs another. The one
thing the instances share is mitmproxy's default confdir, and so a single
certificate authority the operator installs once.

`command` builds the argv and owns the log, `termination` stops a tree, and
`registry` holds what is running.
"""

from .command import DEFAULT_ENVIRONMENT, build_mitmweb_command, mitm_env, repo_root
from .registry import (
    any_proxy_running,
    proxy_is_running,
    proxy_status_snapshot,
    start_proxy_process,
    stop_proxy_process,
)

__all__ = [
    "DEFAULT_ENVIRONMENT",
    "any_proxy_running",
    "build_mitmweb_command",
    "mitm_env",
    "proxy_is_running",
    "proxy_status_snapshot",
    "repo_root",
    "start_proxy_process",
    "stop_proxy_process",
]
