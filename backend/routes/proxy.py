from __future__ import annotations

from typing import Any

from flask import jsonify, request

from backend.proxy.rule_engine import evaluate_http_payload
from backend.proxy.utils import evaluation_result_to_dict

from . import api_bp

_LOCALHOST_ADDRS = frozenset({"127.0.0.1", "::1", "localhost"})


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
    if request.remote_addr not in _LOCALHOST_ADDRS:
        return jsonify({"error": "This endpoint is only available from localhost"}), 403

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
