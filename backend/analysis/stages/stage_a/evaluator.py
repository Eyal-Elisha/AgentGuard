"""Stage A evaluator — orchestrates deterministic and contextual rule execution."""

from __future__ import annotations

from typing import List, Mapping, Optional

from backend.feature_extraction.feature_extractor import ExtractedFeatures
from backend.analysis.rules import (
    CONTEXTUAL_RULES,
    DETERMINISTIC_RULES,
    RULE_WEIGHTS,
    HIGH_RISK_THRESHOLD,
    WARN_THRESHOLD,
    AMBIGUOUS_LOW,
    STAGE_B_LOW,
    STAGE_B_HIGH,
    Decision,
    EvaluationResult,
    RuleResult,
    RuleType,
    SessionContext,
)
from backend.analysis.stages.stage_a.deterministic_rules import RULE_FN, rule_custom_blacklist


def _run_contextual_rules(
    features: ExtractedFeatures,
    session: SessionContext,
    enabled_rules: Optional[Mapping[str, bool]] = None,
) -> List[RuleResult]:
    """
    Placeholder for cheap session-aware rule evaluation.
    Returns an empty list until the session model is in place.
    """
    results: List[RuleResult] = []
    for rule_def in CONTEXTUAL_RULES:
        if not _is_rule_enabled(rule_def.rule_id, enabled_rules):
            continue
    return results


def _is_rule_enabled(rule_id: str, enabled_rules: Optional[Mapping[str, bool]]) -> bool:
    if enabled_rules is None:
        return True
    return enabled_rules.get(rule_id, True)


def _aggregate(results: List[RuleResult]) -> float:
    """Weighted average over all executed (non-skipped) rules."""
    total_weight = 0.0
    weighted_sum = 0.0
    for r in results:
        if r.score is None:
            continue
        w = RULE_WEIGHTS.get(r.rule_id, 0.0)
        weighted_sum += r.score * w
        total_weight += w
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def _make_decision(risk_score: float) -> Decision:
    if risk_score >= HIGH_RISK_THRESHOLD:
        return Decision.BLOCK
    if risk_score >= WARN_THRESHOLD:
        return Decision.WARN
    return Decision.ALLOW


class StageAEvaluator:
    """
    Executes Stage A (cheap rule evaluation) against extracted page features.

    Parameters
    ----------
    custom_blacklist:
        Optional set of domains / full URLs blocked by Rule 9.
    """

    def __init__(self, custom_blacklist: Optional[frozenset] = None) -> None:
        self.custom_blacklist: frozenset = custom_blacklist or frozenset()

    def evaluate(
        self,
        features: ExtractedFeatures,
        session: Optional[SessionContext] = None,
        enabled_rules: Optional[Mapping[str, bool]] = None,
    ) -> EvaluationResult:
        if session is None:
            session = SessionContext()

        rule_results: List[RuleResult] = []
        hard_block_triggered = False

        # ── Step 1: Deterministic rules ──────────────────────────────────────
        for i, rule_def in enumerate(DETERMINISTIC_RULES):
            if not _is_rule_enabled(rule_def.rule_id, enabled_rules):
                continue

            if rule_def.rule_id == "custom_blacklist":
                score, explanation = rule_custom_blacklist(features, self.custom_blacklist)
            else:
                score, explanation = RULE_FN[rule_def.rule_id](features)

            triggered = score > 0.0
            rule_results.append(RuleResult(
                rule_id=rule_def.rule_id,
                rule_type=RuleType.DETERMINISTIC,
                score=score,
                hard_block=rule_def.hard_block,
                explanation=explanation,
                triggered=triggered,
            ))

            if triggered and rule_def.hard_block:
                hard_block_triggered = True
                for remaining in DETERMINISTIC_RULES[i + 1:]:
                    rule_results.append(RuleResult(
                        rule_id=remaining.rule_id,
                        rule_type=RuleType.DETERMINISTIC,
                        score=None,
                        hard_block=remaining.hard_block,
                        explanation="Skipped — prior hard-block rule triggered",
                        triggered=False,
                    ))
                break

        if hard_block_triggered:
            return EvaluationResult(
                decision=Decision.BLOCK,
                risk_score=1.0,
                rule_results=rule_results,
                hard_block_triggered=True,
                stage_b_required=False,
            )

        # ── Step 2: Initial deterministic score ──────────────────────────────
        initial_score = _aggregate(rule_results)

        # ── Step 3: Contextual rules (ambiguous range only) ───────────────────
        contextual_results: List[RuleResult] = []
        if AMBIGUOUS_LOW <= initial_score < HIGH_RISK_THRESHOLD:
            contextual_results = _run_contextual_rules(features, session, enabled_rules)

        all_results = rule_results + contextual_results
        final_score = _aggregate(all_results) if contextual_results else initial_score

        # ── Step 4: Flag whether Stage B is needed ────────────────────────────
        stage_b_required = STAGE_B_LOW <= final_score < STAGE_B_HIGH

        return EvaluationResult(
            decision=_make_decision(final_score),
            risk_score=round(final_score, 4),
            rule_results=all_results,
            hard_block_triggered=False,
            stage_b_required=stage_b_required,
        )
