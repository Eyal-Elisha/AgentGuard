from __future__ import annotations

import datetime
import json
from typing import Any, Dict, Optional

from mitmproxy import http

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


def build_request_data(flow):
    data = {
        "timestamp": _utc_timestamp(),
        "type": "REQUEST",
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "host": flow.request.host,
        "environment": "prod",
        "headers": dict(flow.request.headers),
        "body": safe_get_text(flow.request),
    }
    agent_name = flow.request.headers.get("x-agentguard-agent") or flow.request.headers.get("x-agent-name")
    if isinstance(agent_name, str) and agent_name.strip():
        data["agent_name"] = agent_name
    return data


def build_enforcement_data(flow: http.HTTPFlow) -> Optional[Dict[str, Any]]:
    enforcement = flow.metadata.get("agentguard_enforcement")
    if isinstance(enforcement, dict):
        return enforcement
    return None


def build_response_data(flow):
    return {
        "timestamp": _utc_timestamp(),
        "type": "RESPONSE",
        "status_code": flow.response.status_code,
        "url": flow.request.pretty_url,
        "headers": dict(flow.response.headers),
        "body": safe_get_text(flow.response),
    }


def response_data_with_evaluation(
    flow: http.HTTPFlow,
    result: Optional[EvaluationResult],
) -> Dict[str, Any]:
    data: Dict[str, Any] = build_response_data(flow)
    enforcement = build_enforcement_data(flow)
    if enforcement is not None:
        data["request_enforcement"] = enforcement
    if result is not None:
        data["evaluation"] = evaluation_result_to_dict(result)
    return data


def pretty_print(title, data):
    print(f"\n===== {title} =====", flush=True)
    try:
        display = data
        if isinstance(data, dict) and "evaluation" in data:
            ev = data.get("evaluation") or {}
            if isinstance(ev, dict) and "rule_results" in ev:
                display = dict(data)
                display_ev = dict(ev)
                display_ev["rule_results"] = [r for r in ev.get("rule_results", []) if r.get("score", None) not in (None, 0)]
                display["evaluation"] = display_ev
        print(json.dumps(display, indent=2, ensure_ascii=False), flush=True)
    except Exception:
        # Fallback to printing the original data if anything goes wrong
        print(json.dumps(data, indent=2, ensure_ascii=False), flush=True)
    print(f"===== End =====\n", flush=True)


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
