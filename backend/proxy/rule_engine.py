"""Run Stage A (and Stage B if needed) evaluation for proxy traffic."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.custom_blacklist import custom_blacklist_file_path, load_custom_blacklist_file
from backend.analysis.rules import EvaluationResult
from backend.analysis.stages.stage_a import StageAEvaluator
from backend.analysis.scoring import aggregate_risk_score, decide
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

    if not stage_a_result.stage_b_required or stage_a_result.hard_block_triggered:
        return stage_a_result

    semantic_results = _stage_b.evaluate(features, enabled_rules=enablement)
    combined = stage_a_result.rule_results + semantic_results
    final_score = aggregate_risk_score(combined)

    return EvaluationResult(
        decision=decide(final_score),
        risk_score=round(final_score, 4),
        rule_results=combined,
        hard_block_triggered=False,
        stage_b_required=False,
    )
