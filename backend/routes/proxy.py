from __future__ import annotations

import ipaddress
from typing import Any

from flask import jsonify, request

from backend.proxy.rule_engine import evaluate_http_payload
from backend.proxy.utils import evaluation_result_to_dict

from . import api_bp

try:
    from proxy_launcher import (
        proxy_is_running,
        start_proxy_process,
        stop_proxy_process,
    )
except ImportError:  # pragma: no cover - alternate cwd
    proxy_is_running = None  # type: ignore[assignment, misc]
    start_proxy_process = None  # type: ignore[assignment, misc]
    stop_proxy_process = None  # type: ignore[assignment, misc]

_LOCALHOST_ADDRS = frozenset({"127.0.0.1", "::1"})


def _is_trusted_client(remote_addr: str | None) -> bool:
    """Allow localhost and RFC1918 private LAN clients (dev-friendly)."""
    if not remote_addr:
        return False
    if remote_addr in _LOCALHOST_ADDRS:
        return True
    try:
        ip = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False
    return ip.is_private


def _require_non_empty_string(payload: dict[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _normalize_headers(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): str(item) for key, item in value.items()}


@api_bp.route("/proxy/decision", methods=["POST"])
def proxy_decision():
    if not _is_trusted_client(request.remote_addr):
        return jsonify({"error": "This endpoint is only available from a trusted local network client"}), 403

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON request body is required"}), 400

    required_fields = ("url", "method", "headers", "body")
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    url = _require_non_empty_string(payload, "url")
    if url is None:
        return jsonify({"error": "'url' must be a non-empty string"}), 400

    method = _require_non_empty_string(payload, "method")
    if method is None:
        return jsonify({"error": "'method' must be a non-empty string"}), 400

    headers = _normalize_headers(payload["headers"])
    if headers is None:
        return jsonify({"error": "'headers' must be an object"}), 400

    body = payload["body"]
    if isinstance(body, str):
        body = body.encode("utf-8", errors="replace")
    elif body is None:
        body = b""
    elif not isinstance(body, bytes):
        body = str(body).encode("utf-8", errors="replace")

    result = evaluate_http_payload(
        url=url,
        method=method.upper(),
        headers=headers,
        body=body,
    )
    return jsonify(
        {
            "decision": result.decision.value,
            "evaluation": evaluation_result_to_dict(result),
        }
    ), 200


@api_bp.route("/proxy/status", methods=["GET"])
def proxy_status():
    if not _is_trusted_client(request.remote_addr):
        return jsonify({"error": "This endpoint is only available from a trusted local network client"}), 403
    if proxy_is_running is None:
        return jsonify({"error": "Proxy launcher is not available on this server"}), 503
    return jsonify({"active": proxy_is_running()}), 200


@api_bp.route("/proxy/control", methods=["POST", "OPTIONS"])
def proxy_control():
    """Start or stop mitmweb with `traffic_interception.py` (same as `python proxy_launcher.py`)."""
    if request.method == "OPTIONS":
        return "", 204
    if not _is_trusted_client(request.remote_addr):
        return jsonify({"error": "This endpoint is only available from a trusted local network client"}), 403
    if start_proxy_process is None or stop_proxy_process is None:
        return jsonify({"error": "Proxy launcher is not available on this server"}), 503

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON request body is required"}), 400
    active = payload.get("active")
    if not isinstance(active, bool):
        return jsonify({"error": "'active' must be a boolean"}), 400

    if active:
        ok, message = start_proxy_process()
    else:
        ok, message = stop_proxy_process()

    running = proxy_is_running()
    if not ok:
        return jsonify({"error": message, "active": running}), 500
    return jsonify({"active": running, "message": message}), 200
