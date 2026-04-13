from __future__ import annotations

import logging
from typing import Any, Dict

import requests

from backend.analysis.rules import Decision
from backend.settings import get_backend_decision_url, get_backend_timeout_seconds

from .enforcement import (
    BackendDecision,
    backend_failure_reason,
    build_backend_block_reason,
    decision_reason,
    failure_decision,
)

_logger = logging.getLogger(__name__)


def fetch_backend_decision(payload: Dict[str, Any]) -> BackendDecision:
    session = requests.Session()
    session.trust_env = False
    timeout_seconds = get_backend_timeout_seconds()

    try:
        decision_url = get_backend_decision_url()
        response = session.post(decision_url, json=payload, timeout=timeout_seconds)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise TypeError("response body must be a JSON object")
        decision = Decision(str(data["decision"]).lower())
        evaluation = data.get("evaluation")
        evaluation_dict = evaluation if isinstance(evaluation, dict) else None
        passive_mode = bool(data.get("passive_mode", False))
        reason = (
            build_backend_block_reason(evaluation_dict)
            if decision == Decision.BLOCK
            else decision_reason(decision)
        )
        return BackendDecision(
            decision=decision,
            reason=reason,
            evaluation=evaluation_dict,
            source="backend",
            passive_mode=passive_mode,
        )
    except (KeyError, ValueError, TypeError) as exc:
        _logger.exception("[AgentGuard] Invalid backend decision payload")
        return failure_decision(
            source="backend_error",
            reason=backend_failure_reason("backend_error"),
        )
    except requests.Timeout:
        _logger.warning("[AgentGuard] Backend decision timed out after %.1fs", timeout_seconds)
        return failure_decision(
            source="backend_timeout",
            reason=backend_failure_reason("backend_timeout"),
        )
    except requests.RequestException as exc:
        _logger.exception("[AgentGuard] Backend decision request failed")
        return failure_decision(
            source="backend_unreachable",
            reason=backend_failure_reason("backend_unreachable"),
        )
    finally:
        session.close()
