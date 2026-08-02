"""Run Stage A (and Stage B if needed) evaluation for proxy traffic."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.custom_blacklist import custom_blacklist_file_path, load_custom_blacklist_file
from backend.analysis import meta_classifier
from backend.analysis.rules import (
    Decision,
    EvaluationResult,
    META_HIGH_RISK_THRESHOLD,
    META_WARN_THRESHOLD,
)
from backend.analysis.stages.stage_a import StageAEvaluator
from backend.analysis.stages.stage_a.evaluator import _aggregate, _make_decision
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


def _rule_enablement_map() -> dict[str, bool]:
    try:
        rows = store.rules_list_asc()
    except Exception:
        return {}
    return {str(row["rule_code"]): bool(row["is_enabled"]) for row in rows}


def _meta_decision(prob: float) -> Decision:
    if prob >= META_HIGH_RISK_THRESHOLD:
        return Decision.BLOCK
    if prob >= META_WARN_THRESHOLD:
        return Decision.WARN
    return Decision.ALLOW


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
    enablement = _rule_enablement_map()
    stage_a_result = _stage_a.evaluate(
        features,
        session=session,
        enabled_rules=enablement,
    )

    if stage_a_result.hard_block_triggered:
        return stage_a_result

    meta_on = meta_classifier.is_available()

    # With the trained meta-classifier we always run Stage B so its feature
    # vector is complete (it was trained with semantic scores present). Without
    # it, keep the cheap gate: skip Stage B when Stage A did not request it.
    if not meta_on and not stage_a_result.stage_b_required:
        return stage_a_result

    semantic_results = _stage_b.evaluate(features, enabled_rules=enablement)
    combined = stage_a_result.rule_results + semantic_results

    meta_prob = meta_classifier.score(combined) if meta_on else None
    if meta_prob is not None:
        return EvaluationResult(
            decision=_meta_decision(meta_prob),
            risk_score=round(meta_prob, 4),
            rule_results=combined,
            hard_block_triggered=False,
            stage_b_required=False,
        )

    final_score = _aggregate(combined)
    return EvaluationResult(
        decision=_make_decision(final_score),
        risk_score=round(final_score, 4),
        rule_results=combined,
        hard_block_triggered=False,
        stage_b_required=False,
    )
