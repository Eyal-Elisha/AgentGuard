"""The triggered-rule rows both interstitials show. Shared so the markup, score
formatting and JS escaping live in one place.
"""

from __future__ import annotations

import html
import json
from typing import Any, Dict, List, Optional

_RULE_KIND_LABELS = {
    "deterministic": "Deterministic",
    "contextual": "Contextual",
    "semantic": "Semantic",
}

_NO_SCORE = "—"  # em dash


def rule_kind_label(rule_type: str) -> str:
    kind = (rule_type or "").lower().strip()
    return _RULE_KIND_LABELS.get(kind) or kind.title() or "Rule"


def format_score(value: Any) -> str:
    """Two-decimal risk score, or an em dash when the rule was skipped."""
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}"
    return _NO_SCORE


def triggered_rules(evaluation: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Pull the triggered rule rows out of a backend evaluation payload.

    The payload arrives over HTTP, so every level is treated as untrusted:
    anything not shaped as expected yields no rows rather than an error.
    """
    if not isinstance(evaluation, dict):
        return []
    rules = evaluation.get("rule_results")
    if not isinstance(rules, list):
        return []
    return [item for item in rules if isinstance(item, dict) and item.get("triggered")]


def _rule_row(rule: Dict[str, Any]) -> str:
    rule_id = html.escape(str(rule.get("rule_id", "")))
    kind = html.escape(rule_kind_label(str(rule.get("rule_type", ""))))
    explanation = html.escape(str(rule.get("explanation", "")))
    score = format_score(rule.get("score"))
    return (
        "<li>"
        '<div class="rule-row">'
        f'<span class="rule-id">{rule_id}</span>'
        f'<span class="rule-type">{kind}</span>'
        f'<span class="rule-score">how strong: {score}</span>'
        "</div>"
        f'<div class="rule-explanation">{explanation}</div>'
        "</li>"
    )


def rules_list_html(rules: List[Dict[str, Any]]) -> str:
    return '<ul class="rules-list">' + "".join(_rule_row(r) for r in rules) + "</ul>"


def risk_score_of(evaluation: Optional[Dict[str, Any]]) -> Optional[float]:
    if not isinstance(evaluation, dict):
        return None
    candidate = evaluation.get("risk_score")
    if isinstance(candidate, (int, float)):
        return float(candidate)
    return None


def js_string(value: str) -> str:
    """Encode a string for use as a JS literal inside an inline <script>.

    `</` and `<!` are broken up so the value can never terminate the script
    element early, whatever the caller passes in.
    """
    return json.dumps(value).replace("</", "<\\/").replace("<!", "<\\!")
