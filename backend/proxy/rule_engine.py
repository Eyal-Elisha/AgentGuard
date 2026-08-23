"""Run Stage A (and Stage B if needed) evaluation for proxy traffic."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from backend.custom_blacklist import custom_blacklist_file_path, load_custom_blacklist_file
from backend.analysis.rules import EvaluationResult, RuleResult
from backend.analysis.scoring import (
    aggregate_risk_score,
    apply_decision_floors,
    decide,
    meta_classifier,
)
from backend.analysis.stages.stage_a import StageAEvaluator
from backend.analysis.stages.stage_a.session_loader import build_context
from backend.analysis.stages.stage_b import StageBEvaluator
from backend.feature_extraction.feature_extractor import FeatureExtractor
from backend.storage import sqlite_store as store

_CUSTOM_BLACKLIST = load_custom_blacklist_file(custom_blacklist_file_path())


def get_custom_blacklist() -> frozenset[str]:
    return _CUSTOM_BLACKLIST


def reload_custom_blacklist(entries: frozenset[str]) -> None:
    global _CUSTOM_BLACKLIST
    _CUSTOM_BLACKLIST = entries
    _stage_a.custom_blacklist = _CUSTOM_BLACKLIST


_extractor = FeatureExtractor()
_stage_a = StageAEvaluator(custom_blacklist=_CUSTOM_BLACKLIST)
_stage_b = StageBEvaluator()


def warm_up() -> None:
    """Load the Stage B and meta models now rather than on the first request.

    That first load can outlast the proxy's decision timeout, which fails
    closed on a good page. Called from create_app, so the proxy process does
    not pay for models it never uses.
    """
    try:
        features = _extractor.extract(
            url="https://warmup.invalid/",
            method="GET",
            headers={"Content-Type": "text/html"},
            body=b"<html><body>warmup text to load the semantic models</body></html>",
        )
        meta_classifier.score(_stage_b.evaluate(features, enabled_rules={}))
    except Exception:
        pass


def _rule_settings() -> tuple[dict[str, bool], dict[str, bool]]:
    """The two operator-owned columns: which rules run, and which may hard-block.

    Read together in one query because they come from the same row and the
    engine needs both on every request.
    """
    try:
        rows = store.rules_list_asc()
    except Exception:
        return {}, {}
    enabled = {str(row["rule_code"]): bool(row["is_enabled"]) for row in rows}
    hard_block = {str(row["rule_code"]): bool(row["is_hard_block"]) for row in rows}
    return enabled, hard_block


def _score_and_decide(results: List[RuleResult]) -> EvaluationResult:
    """Turn the full rule set into a score and a decision, preferring the
    trained meta-classifier and falling back to the weighted average."""
    risk = meta_classifier.score(results)
    if risk is not None:
        decision = meta_classifier.decide(risk)
    else:
        risk = aggregate_risk_score(results)
        decision = decide(risk)
    # Applied after scoring, so a rule detecting a threat class the scorer was
    # not trained to predict can still act. Only ever raises the decision, and
    # deliberately leaves the risk score alone: the score reports what the
    # model believes, the decision is what we do about it.
    decision = apply_decision_floors(decision, results)
    return EvaluationResult(
        decision=decision,
        risk_score=round(risk, 4),
        rule_results=results,
        hard_block_triggered=False,
        stage_b_required=False,
    )


def evaluate_http_payload(
    *,
    url: str,
    method: str,
    headers: dict,
    body: bytes | str,
    session_id: Optional[int] = None,
    timestamp: Optional[datetime] = None,
) -> EvaluationResult:
    features = _extractor.extract(
        url=url,
        method=method,
        headers=headers,
        body=body,
    )
    session = build_context(
        session_id=session_id,
        current_timestamp=timestamp,
        current_url=url,
    )
    enablement, hard_block_rules = _rule_settings()
    stage_a_result = _stage_a.evaluate(
        features,
        session=session,
        enabled_rules=enablement,
        hard_block_rules=hard_block_rules,
    )

    if stage_a_result.hard_block_triggered:
        return stage_a_result

    # The meta-classifier was trained with the semantic scores present, so its
    # feature vector is only complete if Stage B has run. When it is in play we
    # therefore always run Stage B; otherwise Stage A's cheap gate stands.
    if not meta_classifier.is_available() and not stage_a_result.stage_b_required:
        return stage_a_result

    semantic_results = _stage_b.evaluate(features, enabled_rules=enablement)
    return _score_and_decide(stage_a_result.rule_results + semantic_results)
