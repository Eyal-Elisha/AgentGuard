"""Diagnostic output from inside mitmproxy. `print` rather than `logging.info`,
because mitmweb's stdout is redirected to a file and no INFO-level handler is
installed.
"""

from __future__ import annotations

ADDON_VERSION = "addon@continue-anyway-ui-suppress-v1"


def diag(message: str) -> None:
    """Write one diagnostic line, forced to ASCII.

    mitmweb's stdout is cp1252 on Windows, and a character outside it raises
    UnicodeEncodeError — which once aborted `handle_request` mid-flight and
    swallowed the bypass redirect.
    """
    safe = message.encode("ascii", errors="replace").decode("ascii")
    print(f"[AgentGuard] {safe}", flush=True)
