"""Whether an agent's port is being served, independent of the registry.

The registry lives in the backend's memory, and mitmweb does not: an instance
outlives a backend restart, and after one the registry no longer knows about a
proxy that is still running and still holding the agent's port.
"""

from __future__ import annotations

import socket

PROBE_HOST = "127.0.0.1"
PROBE_TIMEOUT = 0.25


def port_is_listening(port: int, host: str = PROBE_HOST, timeout: float = PROBE_TIMEOUT) -> bool:
    """Whether anything accepts a connection on `port`."""
    with socket.socket() as probe:
        probe.settimeout(timeout)
        try:
            probe.connect((host, port))
            return True
        except OSError:
            return False
