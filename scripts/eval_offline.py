"""Offline AgentGuard evaluation harness.

Reads a JSONL file of (url, html, label) records and runs each through
AgentGuard's rule engine without the proxy / sessions / database write path.
Emits a JSONL of (url, label, score, decision, hard_block, triggered_rules).

Input record schema (one per line):
    {"url": "...", "html": "...", "label": 0 | 1}
    label = 1 means phishing, 0 means benign.

Usage:
    python scripts/eval_offline.py --input data/sample.jsonl --output runs/scores.jsonl
    python scripts/eval_offline.py --input big.jsonl --output big_scores.jsonl --workers 8

Stage B (the semantic TF-IDF classifier) is enabled by default. Pass --no-stage-b
to evaluate Stage A (deterministic + contextual rules) in isolation.

Speed tips:
- Pass --workers N to parallelize across N processes (defaults to CPU-1).
- The harness defaults to BeautifulSoup's `lxml` parser, ~5-10x faster than
  `html.parser`. Pass --parser html.parser to mirror the production proxy
  exactly (slower but bit-identical to the live runtime).
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
import time
from pathlib import Path
from typing import Iterable, Iterator


# Make `backend` importable when running this script from the repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Per-worker state. Populated by `_worker_init` in each pool process.
# ---------------------------------------------------------------------------

_WORKER: dict = {}


def _patch_bs4_parser(parser: str) -> None:
    """Force BeautifulSoup to use `parser` as the default builder.

    The product code calls `BeautifulSoup(content, "html.parser")` explicitly,
    so we monkey-patch the constructor to override the second arg. lxml is
    drop-in compatible for the calls made by the feature extractor and Stage B
    sanitization, and runs roughly an order of magnitude faster on big pages.
    """
    if parser == "html.parser":
        return
    from bs4 import BeautifulSoup

    original_init = BeautifulSoup.__init__

    def patched_init(self, markup="", features=None, *args, **kwargs):
        if features in (None, "html.parser"):
            features = parser
        return original_init(self, markup, features, *args, **kwargs)

    BeautifulSoup.__init__ = patched_init


def _worker_init(use_stage_b: bool, parser: str) -> None:
    """Per-process setup: import backend, instantiate evaluators once."""
    _patch_bs4_parser(parser)

    from backend.analysis.stages.stage_a import StageAEvaluator
    from backend.analysis.stages.stage_b import StageBEvaluator
    from backend.custom_blacklist import (
        custom_blacklist_file_path,
        load_custom_blacklist_file,
    )
    from backend.feature_extraction.feature_extractor import FeatureExtractor
    from backend.storage import sqlite_store as store

    blacklist = load_custom_blacklist_file(custom_blacklist_file_path())
    _WORKER["extractor"] = FeatureExtractor()
    _WORKER["stage_a"] = StageAEvaluator(custom_blacklist=blacklist)
    _WORKER["stage_b"] = StageBEvaluator() if use_stage_b else None

    try:
        rows = store.rules_list_asc()
        _WORKER["enablement"] = {str(r["rule_code"]): bool(r["is_enabled"]) for r in rows}
    except Exception:
        _WORKER["enablement"] = {}


def _score_one(record: dict) -> dict:
    """Run the pipeline for a single record. Catches per-record exceptions."""
    from backend.analysis.rules import EvaluationResult
    from backend.analysis.stages.stage_a.evaluator import _aggregate, _make_decision
    from backend.analysis.stages.stage_a.session_loader import build_context

    url = record.get("url") or ""
    html = record.get("html") or ""
    label = record.get("label")

    try:
        body = html.encode("utf-8", errors="ignore") if isinstance(html, str) else html
        headers = {"Content-Type": "text/html"}

        extractor = _WORKER["extractor"]
        stage_a = _WORKER["stage_a"]
        stage_b = _WORKER["stage_b"]
        enablement = _WORKER["enablement"]

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
            {"rule_id": r.rule_id, "score": r.score, "hard_block": bool(r.hard_block)}
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
    except Exception as exc:
        return {"url": url, "label": label, "error": f"{type(exc).__name__}: {exc}"}


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


def run_serial(
    records: Iterable[dict],
    *,
    output_path: Path,
    use_stage_b: bool,
    parser: str,
    progress_every: int,
) -> tuple[int, int]:
    _worker_init(use_stage_b=use_stage_b, parser=parser)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    n_total = 0
    n_failed = 0
    start = time.monotonic()
    with output_path.open("w", encoding="utf-8") as out:
        for record in records:
            n_total += 1
            scored = _score_one(record)
            if "error" in scored:
                n_failed += 1
            out.write(json.dumps(scored, ensure_ascii=False) + "\n")
            if progress_every and n_total % progress_every == 0:
                elapsed = time.monotonic() - start
                rate = n_total / elapsed if elapsed > 0 else 0.0
                eta_s = (rate and (n_total / rate)) or 0
                print(f"  scored {n_total} ({rate:.1f}/s, {n_failed} failed)", file=sys.stderr)
    return n_total, n_failed


def run_parallel(
    records: Iterable[dict],
    *,
    output_path: Path,
    use_stage_b: bool,
    parser: str,
    workers: int,
    chunksize: int,
    progress_every: int,
) -> tuple[int, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    n_total = 0
    n_failed = 0
    start = time.monotonic()
    ctx = multiprocessing.get_context("spawn")  # safe on Windows
    with ctx.Pool(
        processes=workers,
        initializer=_worker_init,
        initargs=(use_stage_b, parser),
    ) as pool, output_path.open("w", encoding="utf-8") as out:
        for scored in pool.imap_unordered(_score_one, records, chunksize=chunksize):
            n_total += 1
            if "error" in scored:
                n_failed += 1
            out.write(json.dumps(scored, ensure_ascii=False) + "\n")
            if progress_every and n_total % progress_every == 0:
                elapsed = time.monotonic() - start
                rate = n_total / elapsed if elapsed > 0 else 0.0
                print(f"  scored {n_total} ({rate:.1f}/s, {n_failed} failed)", file=sys.stderr)
    return n_total, n_failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--no-stage-b", action="store_true", help="Skip Stage B (semantic classifier)")
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, (os.cpu_count() or 2) - 1),
        help="Parallel worker processes (default = CPU-1). Use 1 for serial.",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=8,
        help="Records per work-unit handed to each worker. Smaller = smoother progress, bigger = less IPC overhead.",
    )
    parser.add_argument(
        "--parser",
        choices=["lxml", "html.parser"],
        default="lxml",
        help="BeautifulSoup parser (default lxml, much faster).",
    )
    parser.add_argument("--progress-every", type=int, default=100)
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 2

    print(
        f"running with workers={args.workers}, parser={args.parser}, "
        f"stage_b={'off' if args.no_stage_b else 'on'}",
        file=sys.stderr,
    )

    common = dict(
        output_path=args.output,
        use_stage_b=not args.no_stage_b,
        parser=args.parser,
        progress_every=args.progress_every,
    )

    if args.workers <= 1:
        n_total, n_failed = run_serial(_iter_jsonl(args.input), **common)
    else:
        n_total, n_failed = run_parallel(
            _iter_jsonl(args.input),
            workers=args.workers,
            chunksize=args.chunksize,
            **common,
        )

    print(f"done: scored {n_total} records ({n_failed} failed) -> {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
