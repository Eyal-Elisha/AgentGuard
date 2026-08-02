"""Every number the rule engine is calibrated on.

Kept in one module so a change of thresholds or weights is a change to one
file, and so the values can be quoted directly when reporting results.

**Why the thresholds look so low.** Risk is a weighted *average* over the
rules that actually executed — `sum(score x weight) / sum(weight)` — not a
weighted sum. Averaging compresses the result toward zero: with ten cheap
rules in play and one of them firing, the aggregate is roughly that one rule's
weight divided by the total. A page that trips a single strong signal
therefore lands near 0.2, not near 1.0, which is why BLOCK sits at 0.19 rather
than anywhere near the midpoint of [0, 1].

Re-derive these on a dev split with `scripts/calibrate_thresholds.py` before
quoting them anywhere.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

# --- Decision thresholds ---------------------------------------------------

HIGH_RISK_THRESHOLD: float = 0.19  # at or above -> BLOCK
WARN_THRESHOLD: float = 0.15       # at or above, below HIGH -> WARN

# Contextual rules only run when the deterministic score is already ambiguous;
# below this there is nothing for session history to tip either way.
AMBIGUOUS_LOW: float = 0.15

# Stage B gate. Deliberately decoupled from WARN_THRESHOLD: the averaging above
# keeps a weak-but-real signal under the warn line, and if the gate matched
# that line those pages would never reach a semantic check at all.
STAGE_B_LOW: float = 0.0
STAGE_B_HIGH: float = HIGH_RISK_THRESHOLD

# --- Rule enablement -------------------------------------------------------

#: Rules switched off in code until they are recalibrated. This overrides the
#: per-rule toggle in the database — the DB cannot re-enable one of these.
CODE_DISABLED_RULES: frozenset[str] = frozenset({"sensitive_fields"})


def is_rule_enabled(rule_id: str, enabled_rules: Optional[Mapping[str, bool]] = None) -> bool:
    """Whether `rule_id` should run, given the DB toggles for this evaluation."""
    if rule_id in CODE_DISABLED_RULES:
        return False
    if enabled_rules is None:
        return True
    return enabled_rules.get(rule_id, True)


# --- Rule weights ----------------------------------------------------------

RULE_WEIGHTS: Dict[str, float] = {
    "domain_blacklist":       0.25,
    "unencrypted_connection": 0.20,
    # Down-weighted: on webpage HTML this fires on more benign than phishing
    # pages, so a high weight mostly pushed benign pages up. Disabled above.
    "sensitive_fields":       0.10,
    "brand_domain_mismatch":  0.15,
    "unexpected_redirect":    0.10,
    "external_form_action":   0.10,
    "typosquatting":          0.25,
    "ip_based_url":           0.05,
    # Weak on its own (a high-abuse TLD is common enough among benign sites);
    # meant to stack with brand and host signals rather than fire alone.
    "suspicious_tld":         0.05,
    "custom_blacklist":       0.25,

    "sensitive_action_frequency_spike":        0.20,
    "repeated_sensitive_action_after_warning": 0.25,
    "redirect_to_sensitive_action":            0.20,
    "previously_warned_domain_in_session":     0.20,

    "phishing_language":                       0.30,
    "prompt_injection":                        0.30,
}

# --- Contextual rule windows and caps --------------------------------------
# Each contextual rule saturates at `min(count / max_events, 1)`, so
# `max_events` is the count at which the rule reaches a score of 1.0.

CONTEXTUAL_RULE_CONFIG: Dict[str, Dict[str, Any]] = {
    "sensitive_action_frequency_spike": {
        "max_events": 5,
        "window_ms": 60_000,
    },
    "repeated_sensitive_action_after_warning": {"max_events": 5},
    "redirect_to_sensitive_action": {
        "max_events": 5,
        "redirect_window_ms": 2_000,
    },
    "previously_warned_domain_in_session": {"max_events": 5},
}

# --- Semantic rule bindings ------------------------------------------------
# Each semantic rule binds to a trained classifier by `model_id`; the
# classifier's probability is used directly as the rule score. With no model
# artifact present the rule falls back to the keyword heuristic in
# `stage_b.heuristics`, so the pipeline still works on a bare install.

SEMANTIC_RULE_CONFIG: Dict[str, Dict[str, Any]] = {
    "phishing_language": {
        "model_id": "phishing",
        "min_text_chars": 32,
        "trigger_threshold": 0.5,
    },
    "prompt_injection": {
        "model_id": "prompt_injection",
        "min_text_chars": 16,
        # The trained model is over-confident on benign technical text: the
        # public injection corpora outnumber benign instructions roughly 25:1.
        # Real injections score 0.99+, so 0.85 leaves headroom while
        # suppressing that class of false positive.
        "trigger_threshold": 0.85,
    },
}
