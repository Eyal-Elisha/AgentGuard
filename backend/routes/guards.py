"""Route guards applied on top of the auth decorators in `backend.auth`."""

from __future__ import annotations

import ipaddress
from functools import wraps

from flask import jsonify, request

_LOOPBACK_ADDRS = frozenset({"127.0.0.1", "::1"})

_REJECTION = "This endpoint is only available from a trusted local network client"


def is_trusted_client(remote_addr: str | None) -> bool:
    """Loopback and RFC1918 addresses only.

    The proxy runs on the same machine as the backend, so nothing outside the
    local network has a legitimate reason to reach these endpoints. Private
    ranges are allowed because the dashboard is often opened from another
    device on the same LAN during development.
    """
    if not remote_addr:
        return False
    if remote_addr in _LOOPBACK_ADDRS:
        return True
    try:
        return ipaddress.ip_address(remote_addr).is_private
    except ValueError:
        return False


def local_clients_only(view):
    """Reject the request with 403 unless it came from a trusted local client.

    CORS preflights pass through: the browser sends them without credentials
    and the view answers them with a 204 of its own.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        if request.method != "OPTIONS" and not is_trusted_client(request.remote_addr):
            return jsonify({"error": _REJECTION}), 403
        return view(*args, **kwargs)

    return wrapper
