"""Diagnostic output from inside mitmproxy.

`proxy_launcher.py` redirects mitmweb's stdout to `.agentguard/mitmweb.log`, so
printing is what actually reaches a file. `logging.info` does not: mitmproxy
installs no INFO-level handler on the root logger by default and the message is
dropped.
"""

from __future__ import annotations

ADDON_VERSION = "addon@continue-anyway-ui-suppress-v1"


def diag(message: str) -> None:
    """Write one diagnostic line, forced to ASCII.

    On Windows mitmweb's stdout defaults to cp1252, where printing a character
    outside that codepage raises UnicodeEncodeError. That once aborted
    `handle_request` mid-flight and stopped the bypass redirect from being
    sent, so the encoding is not left to chance.
    """
    safe = message.encode("ascii", errors="replace").decode("ascii")
    print(f"[AgentGuard] {safe}", flush=True)
