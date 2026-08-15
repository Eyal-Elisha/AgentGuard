"""Every number the rule engine is calibrated on. The thresholds look low because
risk is a weighted average rather than a sum, so re-derive them with
scripts/calibrate_thresholds.py before quoting them.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

# --- Decision thresholds ---------------------------------------------------
# Calibrated on a domain-disjoint PhreshPhish dev split of 15k rows and
# confirmed on a held-out test split. BLOCK: precision ~0.95 at recall ~0.49.
# WARN: warn-or-block precision ~0.77 at recall ~0.87.

HIGH_RISK_THRESHOLD: float = 0.12  # at or above -> BLOCK
WARN_THRESHOLD: float = 0.04       # at or above, below HIGH -> WARN

# Contextual rules run only on an already-ambiguous deterministic score.
# The gate in stage_a/evaluator.py is AMBIGUOUS_LOW <= score < HIGH_RISK.
# At 0.12 that band is empty, so those four rules never execute. Left as
# calibrated rather than retuned here.
AMBIGUOUS_LOW: float = 0.15

# Stage B gate. Kept separate from WARN_THRESHOLD so a weak but real signal
# still reaches a semantic check instead of stopping under the warn line.
STAGE_B_LOW: float = 0.0
STAGE_B_HIGH: float = HIGH_RISK_THRESHOLD

# --- Meta-classifier thresholds --------------------------------------------
# These apply to scoring/meta_classifier.py, not the weighted average.
# The RAW pair is where the model operates, chosen for a benign false-positive
# budget under 0.5% (WARN recall ~0.43, BLOCK ~0.29 on the fresh set). The
# module rescales onto the round pair for the dashboard. That map is anchored
# on these four values and is monotonic, so it changes no decision.

META_WARN_THRESHOLD: float = 0.50       # at or above, below HIGH -> WARN
META_HIGH_RISK_THRESHOLD: float = 0.80  # at or above -> BLOCK

META_RAW_WARN: float = 0.80   # displays as META_WARN_THRESHOLD
META_RAW_BLOCK: float = 0.93  # displays as META_HIGH_RISK_THRESHOLD

# --- Rule enablement -------------------------------------------------------

# Rules switched off in code until recalibrated. Overrides the per-rule
# toggle in the database, which cannot re-enable one of these.
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
    # Fires on more benign than phishing pages. Disabled above.
    "sensitive_fields":       0.10,
    # Good alongside other rules (403 phish / 5 benign), a coin flip alone
    # (417 / 410). Too low to carry a page over the warn line by itself.
    "brand_domain_mismatch":  0.08,
    "unexpected_redirect":    0.10,
    "external_form_action":   0.10,
    # Down-weighted when is_typosquat was tightened.
    "typosquatting":          0.15,
    "ip_based_url":           0.05,
    # Up from 0.05: phishing clusters on free TLDs, lift ~75x on the eval slice.
    "suspicious_tld":         0.20,
    # Coverage rules for the ~9% of phish scoring near zero. 88 phish / 0
    # benign and 417 / 13 on the eval slice.
    "non_standard_port":      0.20,
    "algorithmic_domain":     0.20,
    "custom_blacklist":       0.25,

    "sensitive_action_frequency_spike":        0.20,
    "repeated_sensitive_action_after_warning": 0.25,
    "redirect_to_sensitive_action":            0.20,
    "previously_warned_domain_in_session":     0.20,

    # Back to full weight after retraining on webpage HTML, lift ~23x.
    "phishing_language":                       0.30,
    "prompt_injection":                        0.30,
}

# --- Contextual rule windows and caps --------------------------------------
# Each rule saturates at min(count / max_events, 1), so max_events is the
# count at which it reaches 1.0.

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
# Each rule binds to a classifier by model_id and uses its probability as the
# score. With no artifact it falls back to the keyword heuristic in
# stage_b.heuristics, so a bare install still works.

SEMANTIC_RULE_CONFIG: Dict[str, Dict[str, Any]] = {
    "phishing_language": {
        "model_id": "phishing",
        "min_text_chars": 32,
        "trigger_threshold": 0.5,
    },
    "prompt_injection": {
        "model_id": "prompt_injection",
        "min_text_chars": 16,
        # Over-confident on benign technical text, since the public injection
        # corpora outnumber benign instructions about 25:1. Real injections
        # score 0.99+, so 0.85 still leaves headroom.
        "trigger_threshold": 0.85,
    },
}
