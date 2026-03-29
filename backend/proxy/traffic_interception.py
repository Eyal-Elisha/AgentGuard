"""Mitmproxy addon: enforce backend request decisions and run Stage A on eligible responses."""

from __future__ import annotations

import sys
from pathlib import Path

from mitmproxy import http

def _bootstrap_repo_path() -> None:
    """Allow mitmproxy to import the package when run from backend/proxy/."""
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


_bootstrap_repo_path()

from backend.proxy.addon import handle_request, handle_response
from backend.settings import load_settings_env

load_settings_env()


def request(flow: http.HTTPFlow):
    handle_request(flow)


def response(flow: http.HTTPFlow):
    handle_response(flow)
