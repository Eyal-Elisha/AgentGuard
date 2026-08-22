from __future__ import annotations

import datetime
import json
import os
from typing import Any, Dict

from backend.analysis.rules import EvaluationResult, RuleResult


def _utc_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def safe_get_text(message):
    if not message or not message.content:
        return ""

    try:
        return message.get_text()

    except Exception:
        return f"<{len(message.content)} bytes binary>"


def _proxy_agent_name(flow) -> str | None:
    header_agent = (
        flow.request.headers.get("x-agentguard-agent")
        or flow.request.headers.get("x-agent-name")
    )
    if isinstance(header_agent, str) and header_agent.strip():
        return header_agent.strip()
    configured_agent = os.environ.get("AGENTGUARD_PROXY_AGENT_NAME", "").strip()
    return configured_agent or None


def _proxy_environment() -> str:
    return os.environ.get("AGENTGUARD_PROXY_ENVIRONMENT", "").strip() or "prod"


def build_request_data(flow):
    data = {
        "timestamp": _utc_timestamp(),
        "type": "REQUEST",
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "host": flow.request.host,
        "environment": _proxy_environment(),
        "headers": dict(flow.request.headers),
        "body": safe_get_text(flow.request),
    }
    agent_name = _proxy_agent_name(flow)
    if agent_name is not None:
        data["agent_name"] = agent_name
    return data


def build_response_payload(flow):
    """Payload for the backend decision endpoint built from the *response*.

    This lets `/api/proxy/decision` run the full HTML feature extraction (and
    therefore exercise the DOM-dependent deterministic rules and the contextual
    rules) for pages the proxy has already received.
    """
    headers = dict(flow.response.headers) if flow.response else {}
    data = {
        "timestamp": _utc_timestamp(),
        "type": "RESPONSE",
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "host": flow.request.host,
        "environment": _proxy_environment(),
        "headers": headers,
        "body": safe_get_text(flow.response) if flow.response else "",
    }
    agent_name = _proxy_agent_name(flow)
    if agent_name is not None:
        data["agent_name"] = agent_name
    return data


def pretty_print(title, data):
    try:
        display = data
        if isinstance(data, dict) and "evaluation" in data:
            ev = data.get("evaluation") or {}
            if isinstance(ev, dict) and "rule_results" in ev:
                display = dict(data)
                display_ev = dict(ev)
                display_ev["rule_results"] = [r for r in ev.get("rule_results", []) if r.get("score", None) not in (None, 0)]
                display["evaluation"] = display_ev
        print(f"\n===== {title} =====", flush=True)
        print(json.dumps(display, indent=2, ensure_ascii=True), flush=True)
        print(f"===== End =====\n", flush=True)
    except Exception:
        try:
            print(json.dumps(data, indent=2, ensure_ascii=True, default=str), flush=True)
        except Exception:
            return


def evaluation_result_to_dict(result: EvaluationResult) -> Dict[str, Any]:
    def rule_dict(r: RuleResult) -> Dict[str, Any]:
        return {
            "rule_id": r.rule_id,
            "rule_type": r.rule_type.value,
            "score": r.score,
            "hard_block": r.hard_block,
            "explanation": r.explanation,
            "triggered": r.triggered,
        }

    return {
        "decision": result.decision.value,
        "risk_score": result.risk_score,
        "hard_block_triggered": result.hard_block_triggered,
        "stage_b_required": result.stage_b_required,
        "rule_results": [rule_dict(r) for r in result.rule_results],
    }
