"""Every number the rule engine is calibrated on.

Kept in one module so a change of thresholds or weights is a change to one
file, and so the values can be quoted directly when reporting results.

**Why the thresholds look so low.** Risk is a weighted *average* over the
rules that actually executed — `sum(score x weight) / sum(weight)` — not a
weighted sum. Averaging compresses the result toward zero: with twelve cheap
rules in play and one of them firing, the aggregate is roughly that one rule's
weight divided by the total. A page that trips a single strong signal
therefore lands near 0.1, not near 1.0, which is why BLOCK sits at 0.12 rather
than anywhere near the midpoint of [0, 1]. Every always-executed rule added
since then has diluted that denominator further.

Re-derive these on a dev split with `scripts/calibrate_thresholds.py` before
quoting them anywhere.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

# --- Decision thresholds ---------------------------------------------------
# Calibrated on a domain-disjoint PhreshPhish dev split (15k rows), then
# confirmed on a held-out test split:
#   BLOCK 0.12 -> block precision ~0.95 at recall ~0.49 (dev)
#   WARN  0.04 -> warn-or-block precision ~0.77 at recall ~0.87 (test)

HIGH_RISK_THRESHOLD: float = 0.12  # at or above -> BLOCK
WARN_THRESHOLD: float = 0.04       # at or above, below HIGH -> WARN

# Contextual rules only run when the deterministic score is already ambiguous;
# below this there is nothing for session history to tip either way.
#
# NOTE: the gate in `stage_a/evaluator.py` is `AMBIGUOUS_LOW <= score <
# HIGH_RISK_THRESHOLD`. Since the recalibration dropped HIGH_RISK_THRESHOLD to
# 0.12, that band is empty and the four contextual rules never execute. Left as
# calibrated rather than silently retuned — see ARCHITECTURE.md.
AMBIGUOUS_LOW: float = 0.15

# Stage B gate. Deliberately decoupled from WARN_THRESHOLD: the averaging above
# keeps a weak-but-real signal under the warn line, and if the gate matched
# that line those pages would never reach a semantic check at all.
STAGE_B_LOW: float = 0.0
STAGE_B_HIGH: float = HIGH_RISK_THRESHOLD

# --- Meta-classifier thresholds --------------------------------------------
# These apply to the stacking layer in `analysis/scoring/meta_classifier.py`,
# not to the weighted average.
#
# The model's real operating points are the RAW pair below, chosen for a
# sub-0.5% benign false-positive budget. On the held-out fresh set: WARN recall
# ~0.43 at ~0.4% benign-warn, BLOCK recall ~0.29 at ~0.1%. Those numbers are
# awkward to read on a dashboard, so the module rescales its output to put the
# cutoffs at 0.50 and 0.80 — a traffic light. The rescaling is monotonic and
# anchored on exactly these four values, so it moves no decision.

META_WARN_THRESHOLD: float = 0.50       # at or above, below HIGH -> WARN
META_HIGH_RISK_THRESHOLD: float = 0.80  # at or above -> BLOCK

META_RAW_WARN: float = 0.80   # model probability that displays as META_WARN_THRESHOLD
META_RAW_BLOCK: float = 0.93  # model probability that displays as META_HIGH_RISK_THRESHOLD

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
    # Excellent as a confirming signal (~403 phish / 5 benign when it fires
    # alongside other rules) but a coin flip alone (~417 phish / 410 benign).
    # Weighted so it cannot carry a page over the warn line by itself.
    "brand_domain_mismatch":  0.08,
    "unexpected_redirect":    0.10,
    "external_form_action":   0.10,
    # Down-weighted along with the tightening in `helpers.is_typosquat`: the
    # old edit-distance logic fired on more benign than phishing pages.
    "typosquatting":          0.15,
    "ip_based_url":           0.05,
    # Up-weighted from 0.05 on eval evidence — phishing pages cluster heavily
    # on free and high-abuse TLDs (lift ~75x on the eval slice).
    "suspicious_tld":         0.20,
    # Coverage rules, added after ~9% of phishing pages were found scoring near
    # zero: no reputation or brand rule caught them. Both clean on the eval
    # slice — non_standard_port 88 phish / 0 benign, algorithmic_domain 417
    # phish / 13 benign (~46x lift).
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
