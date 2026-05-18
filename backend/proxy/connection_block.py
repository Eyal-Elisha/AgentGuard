"""Connection-level blocking for blacklisted non-HTTP flows."""

from __future__ import annotations

from typing import Any

from backend.custom_blacklist import custom_blacklist_matches
from backend.proxy.rule_engine import get_custom_blacklist


def _server_host(flow: Any) -> str:
    try:
        address = flow.server_conn.address
    except Exception:
        return ""

    if isinstance(address, tuple) and address:
        return str(address[0]).lower()
    return ""


def is_blacklisted_connection(flow: Any) -> bool:
    host = _server_host(flow)
    if not host:
        return False
    return custom_blacklist_matches(host, f"https://{host}/", get_custom_blacklist())


def handle_tcp_start(flow: Any) -> None:
    if not is_blacklisted_connection(flow):
        return

    try:
        flow.kill()
    except Exception:
        return
