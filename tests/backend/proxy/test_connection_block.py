"""Connection-level blacklist enforcement."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from backend.proxy.connection_block import handle_tcp_start, is_blacklisted_connection


class KillableFlow(SimpleNamespace):
    def __init__(self, host: str):
        super().__init__(server_conn=SimpleNamespace(address=(host, 443)), killed=False)

    def kill(self):
        self.killed = True


def test_blacklisted_subdomain_connection_matches():
    flow = KillableFlow("api.monkeytype.com")
    with patch("backend.proxy.connection_block.get_custom_blacklist", return_value=frozenset({"monkeytype.com"})):
        assert is_blacklisted_connection(flow) is True


def test_unlisted_connection_does_not_match():
    flow = KillableFlow("cm.g.doubleclick.net")
    with patch("backend.proxy.connection_block.get_custom_blacklist", return_value=frozenset({"monkeytype.com"})):
        assert is_blacklisted_connection(flow) is False


def test_blacklisted_connection_is_killed():
    flow = KillableFlow("api.monkeytype.com")
    with patch("backend.proxy.connection_block.get_custom_blacklist", return_value=frozenset({"monkeytype.com"})):
        handle_tcp_start(flow)
    assert flow.killed is True
