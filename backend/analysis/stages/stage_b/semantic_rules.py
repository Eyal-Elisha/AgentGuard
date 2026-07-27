"""Semantic rule implementations for Stage B.

Each rule receives the sanitized page text plus the rule-specific config (model
id, minimum text length, trigger threshold) and returns `(score, explanation)`.
Score is the classifier's probability that the content is malicious. The rule
is recorded as `triggered` when the score crosses `trigger_threshold`.

Score is `None` (skipped) when there is not enough text to vectorize
meaningfully — this keeps aggregation from being diluted by trivially short
documents.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional, Tuple

from backend.analysis.stages.stage_b.classifier import get_classifier


_PHISHING_EVIDENCE: tuple[tuple[re.Pattern[str], float], ...] = (
    # Explicit credential collection.
    (re.compile(r"\binput:password\b", re.I), 1.4),
    (re.compile(r"\b(?:password|passcode|pin|otp|mfa)\b", re.I), 0.8),
    (re.compile(r"\b(?:seed|recovery)\s+phrase\b", re.I), 1.6),
    (re.compile(r"\bprivate\s+key\b", re.I), 1.6),
    (re.compile(r"\bconnect\s+(?:your\s+)?wallet\b", re.I), 1.2),
    # Account-verification and urgency patterns that are uncommon on normal pages.
    (re.compile(r"\bverify\s+(?:your\s+)?account\b", re.I), 1.5),
    (re.compile(r"\bconfirm\s+(?:your\s+)?identity\b", re.I), 1.4),
    (re.compile(r"\bre[- ]?enter\s+your\s+(?:password|credentials?)\b", re.I), 1.5),
    (re.compile(r"\baccount\s+(?:suspended|locked|disabled|limited)\b", re.I), 1.4),
    (re.compile(r"\b(?:unusual|suspicious)\s+(?:activity|sign[- ]?in|login)\b", re.I), 1.3),
    (re.compile(r"\bsecurity\s+alert\b", re.I), 1.0),
    (re.compile(r"\bwithin\s+\d+\s+(?:hours?|minutes?)\b", re.I), 0.8),
    (re.compile(r"\b(?:avoid|prevent)\s+(?:losing|account)\s+access\b", re.I), 0.8),
)


def _phishing_evidence_score(text: str) -> float:
    """Return lexical evidence that text is specifically credential-phishing."""
    return sum(weight for pattern, weight in _PHISHING_EVIDENCE if pattern.search(text))


def _classifier_label(model_id: str) -> str:
    classifier = get_classifier(model_id)
    return "heuristic fallback" if classifier.using_heuristic else "trained model"


def rule_phishing_language(
    text: str,
    config: Dict[str, Any],
) -> Tuple[Optional[float], str]:
    """Phishing or Credential-Harvesting Language.

    Estimates the probability that the page text contains urgency cues, account
    verification messaging, or credential-collection prompts characteristic of
    phishing kits.
    """
    min_chars = int(config.get("min_text_chars", 32))
    if len(text) < min_chars:
        return None, "Skipped - not enough text content to analyze for phishing language"

    model_id = str(config.get("model_id", "phishing"))
    classifier = get_classifier(model_id)
    raw_score = classifier.predict_proba(text)
    threshold = float(config.get("trigger_threshold", 0.5))
    min_evidence = float(config.get("min_evidence", 0.8))
    weak_evidence = float(config.get("weak_evidence", 1.4))
    strong_model_threshold = float(config.get("strong_model_threshold", 0.75))
    no_evidence_cap = float(config.get("no_evidence_cap", 0.35))
    weak_evidence_cap = float(config.get("weak_evidence_cap", 0.49))

    evidence = _phishing_evidence_score(text)
    score = raw_score
    if evidence < min_evidence:
        score = min(raw_score, no_evidence_cap)
    elif evidence < weak_evidence and raw_score < strong_model_threshold:
        score = min(raw_score, weak_evidence_cap)

    if score >= threshold:
        return score, (
            f"Page text shows phishing or credential-harvesting language "
            f"({_classifier_label(model_id)} score={score:.2f}, evidence={evidence:.1f})."
        )
    return score, (
        f"No phishing-language patterns detected "
        f"({_classifier_label(model_id)} score={score:.2f}, raw={raw_score:.2f}, "
        f"evidence={evidence:.1f})."
    )


def rule_prompt_injection(
    text: str,
    config: Dict[str, Any],
) -> Tuple[Optional[float], str]:
    """Prompt Injection / Instruction Hierarchy Manipulation.

    Estimates the probability that the content tries to override, suppress, or
    redirect the agent's instruction hierarchy (e.g. "ignore previous
    instructions", "reveal hidden prompt", role-override attempts).
    """
    min_chars = int(config.get("min_text_chars", 16))
    if len(text) < min_chars:
        return None, "Skipped - not enough text content to analyze for prompt injection"

    model_id = str(config.get("model_id", "prompt_injection"))
    classifier = get_classifier(model_id)
    score = classifier.predict_proba(text)
    threshold = float(config.get("trigger_threshold", 0.5))

    if score >= threshold:
        return score, (
            f"Content attempts to override the agent's instruction hierarchy "
            f"({_classifier_label(model_id)} score={score:.2f})."
        )
    return score, (
        f"No prompt-injection patterns detected "
        f"({_classifier_label(model_id)} score={score:.2f})."
    )


SEMANTIC_RULE_FN: Dict[str, Callable[[str, Dict[str, Any]], Tuple[Optional[float], str]]] = {
    "phishing_language": rule_phishing_language,
    "prompt_injection":  rule_prompt_injection,
}
