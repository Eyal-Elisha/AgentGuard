"""Run Stage A evaluation and custom-list checks for proxy traffic."""

from __future__ import annotations

from backend.custom_blacklist import custom_blacklist_file_path, load_custom_blacklist_file
from backend.analysis.rules import EvaluationResult
from backend.analysis.stages.stage_a import StageAEvaluator
from backend.feature_extraction.feature_extractor import FeatureExtractor
from backend.storage import sqlite_store as store

_CUSTOM_BLACKLIST = load_custom_blacklist_file(custom_blacklist_file_path())


def get_custom_blacklist() -> frozenset[str]:
    return _CUSTOM_BLACKLIST


_extractor = FeatureExtractor()
_evaluator = StageAEvaluator(custom_blacklist=_CUSTOM_BLACKLIST)


def _rule_enablement_map() -> dict[str, bool]:
    try:
        rows = store.rules_list_asc()
    except Exception:
        # Fail open for rule execution if storage is temporarily unavailable.
        return {}
    return {str(row["rule_code"]): bool(row["is_enabled"]) for row in rows}


def evaluate_http_payload(
    *,
    url: str,
    method: str,
    headers: dict,
    body: bytes | str,
) -> EvaluationResult:
    features = _extractor.extract(
        url=url,
        method=method,
        headers=headers,
        body=body,
    )
    return _evaluator.evaluate(features, enabled_rules=_rule_enablement_map())
