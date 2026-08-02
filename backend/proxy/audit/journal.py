"""Append-only journal of everything the proxy decided.

Records go to the audit logger configured in `backend.audit_logging`, which
encrypts each line before it reaches disk. Keys are sorted so two runs that
decided the same thing produce the same line.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from backend.audit_logging import configure_audit_logger

_logger = logging.getLogger("agentguard.audit")


def iso_z(dt: datetime) -> str:
    """UTC, second resolution, `Z` suffix — the timestamp format of the journal."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_record(record: dict[str, Any]) -> None:
    _audit_logger().info(json.dumps(record, sort_keys=True))


def _audit_logger() -> logging.Logger:
    """The audit logger, configuring it on first use.

    The proxy addon runs inside mitmproxy rather than the Flask app, so it
    cannot rely on `create_app` having set the handlers up.
    """
    if _logger.handlers:
        return _logger
    return configure_audit_logger()
