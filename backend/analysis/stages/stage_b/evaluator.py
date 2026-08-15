"""Runs the semantic rules over the extracted page text and returns their
RuleResults. The orchestrator merges them with Stage A's before re-aggregating.
"""

from __future__ import annotations

import logging
from typing import List, Mapping, Optional

from backend.feature_extraction.feature_extractor import ExtractedFeatures
from backend.analysis.rules import (
    SEMANTIC_RULE_CONFIG,
    SEMANTIC_RULES,
    RuleResult,
    RuleType,
    is_rule_enabled,
)
from backend.analysis.stages.stage_b.sanitization import extract_semantic_text
from backend.analysis.stages.stage_b.semantic_rules import SEMANTIC_RULE_FN

_logger = logging.getLogger(__name__)


class StageBEvaluator:
    """Executes Stage B semantic rules against extracted page features."""

    def evaluate(
        self,
        features: ExtractedFeatures,
        enabled_rules: Optional[Mapping[str, bool]] = None,
    ) -> List[RuleResult]:
        text = extract_semantic_text(features)

        results: List[RuleResult] = []
        for rule_def in SEMANTIC_RULES:
            if not is_rule_enabled(rule_def.rule_id, enabled_rules):
                continue
            rule_fn = SEMANTIC_RULE_FN.get(rule_def.rule_id)
            if rule_fn is None:
                continue
            config = SEMANTIC_RULE_CONFIG.get(rule_def.rule_id, {})
            try:
                score, explanation = rule_fn(text, config)
            except Exception:
                _logger.exception("Semantic rule %s failed", rule_def.rule_id)
                score, explanation = None, "Skipped - semantic rule failed during evaluation"

            threshold = float(config.get("trigger_threshold", 0.5))
            triggered = score is not None and score >= threshold
            results.append(RuleResult(
                rule_id=rule_def.rule_id,
                rule_type=RuleType.SEMANTIC,
                score=score,
                hard_block=rule_def.hard_block,
                explanation=explanation,
                triggered=triggered,
            ))
        return results
