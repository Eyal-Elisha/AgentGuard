"""Every number the rule engine is calibrated on.

Kept in one module so retuning is a change to one file.

The thresholds look low because risk is a weighted *average* over the rules
that ran, not a sum — one rule firing among twelve lands near 0.1, not 1.0.
See `scoring/weighted_average.py`. Re-derive with
`scripts/calibrate_thresholds.py` before quoting these anywhere.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

# --- Decision thresholds ---------------------------------------------------
# From a domain-disjoint PhreshPhish dev split (15k rows), confirmed on a
# held-out test split: BLOCK gives block precision ~0.95 at recall ~0.49,
# WARN gives warn-or-block precision ~0.77 at recall ~0.87.

HIGH_RISK_THRESHOLD: float = 0.12  # at or above -> BLOCK
WARN_THRESHOLD: float = 0.04       # at or above, below HIGH -> WARN

# Contextual rules run only when the deterministic score is already ambiguous.
# The gate in `stage_a/evaluator.py` is `AMBIGUOUS_LOW <= score <
# HIGH_RISK_THRESHOLD`, so at 0.12 that band is empty and those four rules
# never execute. Left as calibrated rather than quietly retuned.
AMBIGUOUS_LOW: float = 0.15

# Stage B gate, decoupled from WARN_THRESHOLD so weak-but-real signals still
# reach a semantic check instead of stopping just under the warn line.
STAGE_B_LOW: float = 0.0
STAGE_B_HIGH: float = HIGH_RISK_THRESHOLD

# --- Meta-classifier thresholds --------------------------------------------
# For `analysis/scoring/meta_classifier.py`, not the weighted average. The RAW
# pair is where the model actually operates, picked for a sub-0.5% benign
# false-positive budget (WARN recall ~0.43, BLOCK ~0.29 on the fresh set). The
# module rescales onto the round pair so the dashboard reads as a traffic
# light; that map is anchored on these four values and is monotonic, so it
# changes no decision.

META_WARN_THRESHOLD: float = 0.50       # at or above, below HIGH -> WARN
META_HIGH_RISK_THRESHOLD: float = 0.80  # at or above -> BLOCK

META_RAW_WARN: float = 0.80   # displays as META_WARN_THRESHOLD
META_RAW_BLOCK: float = 0.93  # displays as META_HIGH_RISK_THRESHOLD

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
    # Confirming signal only: 403 phish / 5 benign alongside other rules, but
    # 417 / 410 alone. Too low to carry a page over the warn line by itself.
    "brand_domain_mismatch":  0.08,
    "unexpected_redirect":    0.10,
    "external_form_action":   0.10,
    # Down-weighted with the tightening in `helpers.is_typosquat`.
    "typosquatting":          0.15,
    "ip_based_url":           0.05,
    # Up from 0.05: phishing clusters on free TLDs (lift ~75x on the eval slice).
    "suspicious_tld":         0.20,
    # Coverage rules for the ~9% of phish that scored near zero — no reputation
    # or brand rule caught them. 88 phish / 0 benign and 417 / 13 respectively.
    "non_standard_port":      0.20,
    "algorithmic_domain":     0.20,
    "custom_blacklist":       0.25,

    "sensitive_action_frequency_spike":        0.20,
    "repeated_sensitive_action_after_warning": 0.25,
    "redirect_to_sensitive_action":            0.20,
    "previously_warned_domain_in_session":     0.20,

    # Retrained on domain-disjoint PhreshPhish webpage HTML, which made them
    # high-precision on real pages (lift ~23x), so both are back at full weight.
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
