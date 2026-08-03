"""The eighteen rules, grouped by type, which is also the order they run in. A
rule with `hard_block=True` short-circuits its stage and forces the risk score
to 1.0.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .models import ComputeClass, RuleDefinition, RuleType
from .tuning import RULE_WEIGHTS


def _deterministic(rule_id: str, description: str, *, hard_block: bool = False) -> RuleDefinition:
    return RuleDefinition(
        rule_id,
        description,
        RuleType.DETERMINISTIC,
        ComputeClass.CHEAP,
        RULE_WEIGHTS[rule_id],
        hard_block=hard_block,
    )


def _contextual(rule_id: str, description: str) -> RuleDefinition:
    return RuleDefinition(
        rule_id,
        description,
        RuleType.CONTEXTUAL,
        ComputeClass.CHEAP,
        RULE_WEIGHTS[rule_id],
        hard_block=False,
    )


def _semantic(rule_id: str, description: str) -> RuleDefinition:
    return RuleDefinition(
        rule_id,
        description,
        RuleType.SEMANTIC,
        ComputeClass.EXPENSIVE,
        RULE_WEIGHTS[rule_id],
        hard_block=False,
    )


DETERMINISTIC_RULES: List[RuleDefinition] = [
    _deterministic("domain_blacklist", "Domain in Popular Blacklist", hard_block=True),
    # No longer a hard block: auto-blocking every plain-HTTP page left an
    # irreducible ~1% false-positive floor, which caps precision at realistic
    # base rates. Credentials over HTTP still block through the aggregate,
    # because the brand and form rules stack on top of this one.
    _deterministic("unencrypted_connection", "Unencrypted or Invalid Secure Connection"),
    # Switched off via CODE_DISABLED_RULES. Fires on more benign than
    # phishing pages until it is recalibrated.
    _deterministic("sensitive_fields", "Sensitive Fields Present"),
    _deterministic("brand_domain_mismatch", "Brand Domain Mismatch"),
    _deterministic("unexpected_redirect", "Unexpected Redirect During Sensitive Interaction"),
    _deterministic("external_form_action", "External Form Action"),
    # No longer a hard block either: it fired on more benign than phishing
    # pages, so blocking on it alone took down legitimate sites.
    _deterministic("typosquatting", "Typosquatting Domain Detection"),
    _deterministic("ip_based_url", "IP Based URL Usage"),
    _deterministic("suspicious_tld", "High-Abuse Top-Level Domain"),
    _deterministic("non_standard_port", "Non-Standard Port"),
    _deterministic("algorithmic_domain", "Algorithmically-Generated Domain"),
    _deterministic("custom_blacklist", "Custom Local Blacklist", hard_block=True),
]

CONTEXTUAL_RULES: List[RuleDefinition] = [
    _contextual("sensitive_action_frequency_spike", "Several risky pages in a short time"),
    _contextual(
        "repeated_sensitive_action_after_warning",
        "More risky pages after you were already warned",
    ),
    _contextual("redirect_to_sensitive_action", "Arrived here through a fast chain of redirects"),
    _contextual(
        "previously_warned_domain_in_session",
        "Back to a site we already flagged this session",
    ),
]

SEMANTIC_RULES: List[RuleDefinition] = [
    _semantic("phishing_language", "Phishing or Credential-Harvesting Language"),
    _semantic("prompt_injection", "Prompt Injection / Instruction Hierarchy Manipulation"),
]

#: Every rule, in execution order. Used to seed the `rules` table at startup.
ALL_RULES: Tuple[RuleDefinition, ...] = (
    *DETERMINISTIC_RULES,
    *CONTEXTUAL_RULES,
    *SEMANTIC_RULES,
)

RULES_BY_ID: Dict[str, RuleDefinition] = {rule.rule_id: rule for rule in ALL_RULES}
