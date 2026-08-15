"""Stage A evaluator — orchestrates deterministic and contextual rule execution."""

from __future__ import annotations

from typing import List, Mapping, Optional

from backend.feature_extraction.feature_extractor import ExtractedFeatures
from backend.analysis.rules import (
    AMBIGUOUS_LOW,
    CONTEXTUAL_RULES,
    CONTEXTUAL_RULE_CONFIG,
    DETERMINISTIC_RULES,
    HIGH_RISK_THRESHOLD,
    STAGE_B_HIGH,
    STAGE_B_LOW,
    Decision,
    EvaluationResult,
    RuleResult,
    RuleType,
    SessionContext,
    is_rule_enabled,
)
from backend.analysis.scoring import aggregate_risk_score, decide
from backend.analysis.stages.stage_a.contextual_rules import CONTEXTUAL_RULE_FN
from backend.analysis.stages.stage_a.deterministic_rules import RULE_FN, rule_custom_blacklist


def _run_contextual_rules(
    features: ExtractedFeatures,
    session: SessionContext,
    enabled_rules: Optional[Mapping[str, bool]] = None,
) -> List[RuleResult]:
    """Run all enabled contextual rules against the supplied session snapshot.

    Contextual rules may return a `None` score to indicate they were skipped
    (preconditions not met). Skipped results are still included in
    `rule_results` for full audit history but excluded from aggregation by
    `aggregate_risk_score`.
    """
    results: List[RuleResult] = []
    for rule_def in CONTEXTUAL_RULES:
        if not is_rule_enabled(rule_def.rule_id, enabled_rules):
            continue
        rule_fn = CONTEXTUAL_RULE_FN.get(rule_def.rule_id)
        if rule_fn is None:
            continue
        config = CONTEXTUAL_RULE_CONFIG.get(rule_def.rule_id, {})
        score, explanation = rule_fn(session, config)
        triggered = score is not None and score > 0.0
        results.append(RuleResult(
            rule_id=rule_def.rule_id,
            rule_type=RuleType.CONTEXTUAL,
            score=score,
            hard_block=rule_def.hard_block,
            explanation=explanation,
            triggered=triggered,
        ))
    return results


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
            if not is_rule_enabled(rule_def.rule_id, enabled_rules):
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
        initial_score = aggregate_risk_score(rule_results)

        # ── Step 3: Contextual rules (ambiguous range only) ───────────────────
        contextual_results: List[RuleResult] = []
        if AMBIGUOUS_LOW <= initial_score < HIGH_RISK_THRESHOLD:
            contextual_results = _run_contextual_rules(features, session, enabled_rules)

        all_results = rule_results + contextual_results
        final_score = aggregate_risk_score(all_results) if contextual_results else initial_score

        # ── Step 4: Flag whether Stage B is needed ────────────────────────────
        stage_b_required = STAGE_B_LOW <= final_score < STAGE_B_HIGH

        return EvaluationResult(
            decision=decide(final_score),
            risk_score=round(final_score, 4),
            rule_results=all_results,
            hard_block_triggered=False,
            stage_b_required=stage_b_required,
        )
