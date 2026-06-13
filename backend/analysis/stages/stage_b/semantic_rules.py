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

from typing import Any, Callable, Dict, Optional, Tuple

from backend.analysis.stages.stage_b.classifier import get_classifier


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
    score = classifier.predict_proba(text)
    threshold = float(config.get("trigger_threshold", 0.5))

    if score >= threshold:
        return score, (
            f"Page text shows phishing or credential-harvesting language "
            f"({_classifier_label(model_id)} score={score:.2f})."
        )
    return score, (
        f"No phishing-language patterns detected "
        f"({_classifier_label(model_id)} score={score:.2f})."
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
