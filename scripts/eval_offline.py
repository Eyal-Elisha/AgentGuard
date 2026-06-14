"""Offline AgentGuard evaluation harness.

Reads a JSONL file of (url, html, label) records and runs each through
AgentGuard's rule engine without the proxy / sessions / database write path.
Emits a JSONL of (url, label, score, decision, hard_block, triggered_rules).

Input record schema (one per line):
    {"url": "...", "html": "...", "label": 0 | 1}
    label = 1 means phishing, 0 means benign.

Usage:
    python scripts/eval_offline.py --input data/sample.jsonl --output runs/scores.jsonl

Stage B (the semantic TF-IDF classifier) is enabled by default. Pass --no-stage-b
to evaluate Stage A (deterministic + contextual rules) in isolation.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Iterator


# Make `backend` importable when running this script from the repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.analysis.rules import EvaluationResult  # noqa: E402
from backend.analysis.stages.stage_a import StageAEvaluator  # noqa: E402
from backend.analysis.stages.stage_a.evaluator import _aggregate, _make_decision  # noqa: E402
from backend.analysis.stages.stage_a.session_loader import build_context  # noqa: E402
from backend.analysis.stages.stage_b import StageBEvaluator  # noqa: E402
from backend.custom_blacklist import (  # noqa: E402
    custom_blacklist_file_path,
    load_custom_blacklist_file,
)
from backend.feature_extraction.feature_extractor import FeatureExtractor  # noqa: E402
from backend.storage import sqlite_store as store  # noqa: E402


def _rule_enablement_map() -> dict[str, bool]:
    try:
        rows = store.rules_list_asc()
    except Exception:
        return {}
    return {str(row["rule_code"]): bool(row["is_enabled"]) for row in rows}


def _iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"warn: skipping line {i}: {exc}", file=sys.stderr)


def _score_record(
    record: dict,
    *,
    stage_a: StageAEvaluator,
    stage_b: StageBEvaluator | None,
    extractor: FeatureExtractor,
    enablement: dict[str, bool],
) -> dict:
    url = record.get("url") or ""
    html = record.get("html") or ""
    label = record.get("label")

    body = html.encode("utf-8", errors="ignore") if isinstance(html, str) else html
    headers = {"Content-Type": "text/html"}

    features = extractor.extract(url=url, method="GET", headers=headers, body=body)
    session = build_context(session_id=None, current_timestamp=None, current_url=url)

    stage_a_result = stage_a.evaluate(features, session=session, enabled_rules=enablement)

    if stage_b is None or stage_a_result.hard_block_triggered or not stage_a_result.stage_b_required:
        result = stage_a_result
        stage_b_ran = False
    else:
        semantic_results = stage_b.evaluate(features, enabled_rules=enablement)
        combined = stage_a_result.rule_results + semantic_results
        final_score = _aggregate(combined)
        result = EvaluationResult(
            decision=_make_decision(final_score),
            risk_score=round(final_score, 4),
            rule_results=combined,
            hard_block_triggered=False,
            stage_b_required=False,
        )
        stage_b_ran = True

    triggered = [
        {
            "rule_id": r.rule_id,
            "score": r.score,
            "hard_block": bool(r.hard_block),
        }
        for r in result.rule_results
        if r.triggered
    ]

    return {
        "url": url,
        "label": label,
        "score": float(result.risk_score),
        "decision": result.decision.value if hasattr(result.decision, "value") else str(result.decision),
        "hard_block": bool(result.hard_block_triggered),
        "stage_b_ran": stage_b_ran,
        "triggered_rules": triggered,
    }


def run(
    records: Iterable[dict],
    *,
    output_path: Path,
    use_stage_b: bool,
    progress_every: int,
) -> tuple[int, int]:
    blacklist = load_custom_blacklist_file(custom_blacklist_file_path())
    extractor = FeatureExtractor()
    stage_a = StageAEvaluator(custom_blacklist=blacklist)
    stage_b = StageBEvaluator() if use_stage_b else None
    enablement = _rule_enablement_map()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    n_total = 0
    n_failed = 0
    start = time.monotonic()
    with output_path.open("w", encoding="utf-8") as out:
        for record in records:
            n_total += 1
            try:
                scored = _score_record(
                    record,
                    stage_a=stage_a,
                    stage_b=stage_b,
                    extractor=extractor,
                    enablement=enablement,
                )
            except Exception as exc:
                n_failed += 1
                scored = {
                    "url": record.get("url"),
                    "label": record.get("label"),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            out.write(json.dumps(scored, ensure_ascii=False) + "\n")
            if progress_every and n_total % progress_every == 0:
                elapsed = time.monotonic() - start
                rate = n_total / elapsed if elapsed > 0 else 0.0
                print(f"  scored {n_total} ({rate:.1f}/s, {n_failed} failed)", file=sys.stderr)

    return n_total, n_failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="JSONL input")
    parser.add_argument("--output", required=True, type=Path, help="JSONL output")
    parser.add_argument("--no-stage-b", action="store_true", help="Skip Stage B (semantic classifier)")
    parser.add_argument("--progress-every", type=int, default=100)
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 2

    n_total, n_failed = run(
        _iter_jsonl(args.input),
        output_path=args.output,
        use_stage_b=not args.no_stage_b,
        progress_every=args.progress_every,
    )
    print(f"done: scored {n_total} records ({n_failed} failed) -> {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
