"""Emit the full per-rule score vector for each page, for training a meta-classifier
over the rule outputs (an alternative to the hand-weighted-average aggregation).

Output JSONL: {"label": 0|1, "feat": {rule_id: score, ...}} where score is the
raw rule score (0.0 for not-fired / skipped). Semantic rules always run
(stage_b_always) so their probability is captured even below trigger threshold.

Usage:
    python scripts/build_rule_features.py --input data/dev.jsonl --output runs/dev_feats.jsonl
"""
from __future__ import annotations
import argparse, json, multiprocessing, os, sys, warnings
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_W: dict = {}


def _init(parser: str) -> None:
    warnings.filterwarnings("ignore")
    if parser != "html.parser":
        from bs4 import BeautifulSoup
        orig = BeautifulSoup.__init__
        def patched(self, markup="", features=None, *a, **k):
            if features in (None, "html.parser"): features = parser
            return orig(self, markup, features, *a, **k)
        BeautifulSoup.__init__ = patched
    from backend.analysis.stages.stage_a import blacklist as bl
    bl.blacklist_cache.is_listed = lambda d: (False, "offline")  # type: ignore
    from backend.analysis.stages.stage_a import StageAEvaluator
    from backend.analysis.stages.stage_b import StageBEvaluator
    from backend.feature_extraction.feature_extractor import FeatureExtractor
    _W["ex"] = FeatureExtractor()
    _W["a"] = StageAEvaluator()
    _W["b"] = StageBEvaluator()


def _one(rec: dict) -> dict | None:
    from backend.analysis.stages.stage_a.session_loader import build_context
    url = rec.get("url") or ""; html = rec.get("html") or ""; label = rec.get("label")
    if label not in (0, 1): return None
    try:
        body = html.encode("utf-8", "ignore")
        f = _W["ex"].extract(url=url, method="GET", headers={"Content-Type": "text/html"}, body=body)
        sess = build_context(session_id=None, current_timestamp=None, current_url=url)
        a = _W["a"].evaluate(f, session=sess, enabled_rules={})
        feat = {}
        for r in a.rule_results:
            feat[r.rule_id] = float(r.score) if r.score is not None else 0.0
        feat["_hard_block"] = 1.0 if a.hard_block_triggered else 0.0
        if not a.hard_block_triggered:
            for r in _W["b"].evaluate(f, enabled_rules={}):
                feat[r.rule_id] = float(r.score) if r.score is not None else 0.0
        return {"label": label, "feat": feat}
    except Exception as exc:
        return {"label": label, "error": f"{type(exc).__name__}: {exc}"}


def _rows_from_parquet(index_path: Path, parquet_glob: str):
    """Yield {url, html, label} by joining an index of ids to the parquet shards.

    An index names rows by sha256; the HTML stays where it already is. A 1%
    benchmark is ~91k pages, so materialising it as JSONL would run to tens of
    GB of duplicated markup for a run that reads each page once.
    """
    import pyarrow.parquet as pq

    wanted: dict[str, int] = {}
    with index_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("sha256"):
                wanted[rec["sha256"]] = int(rec.get("label", 0))
    print(f"  index: {len(wanted)} ids", file=sys.stderr)

    pattern = Path(parquet_glob)
    files = sorted(pattern.parent.glob(pattern.name))
    if not files:
        raise SystemExit(f"error: no parquet matched {parquet_glob!r}")
    seen = 0
    for path in files:
        table = pq.read_table(str(path), columns=["sha256", "url", "html"])
        for row in table.to_pylist():
            sha = row.get("sha256")
            if sha in wanted:
                seen += 1
                yield {"url": row.get("url") or "", "html": row.get("html") or "",
                       "label": wanted[sha]}
    if seen < len(wanted):
        print(f"  note: {len(wanted) - seen} ids not found in the shards", file=sys.stderr)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path,
                    help="JSONL of {url, html, label}, or an index of {sha256, label} "
                         "when --parquet-glob is given")
    ap.add_argument("--parquet-glob",
                    help="Read HTML from these shards, joining on the sha256 in --input")
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--parser", default="lxml")
    ap.add_argument("--progress-every", type=int, default=10000)
    args = ap.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.parquet_glob:
        rows = _rows_from_parquet(args.input, args.parquet_glob)
    else:
        rows = (json.loads(l) for l in args.input.open(encoding="utf-8") if l.strip())
    ctx = multiprocessing.get_context("spawn")
    n = 0
    with ctx.Pool(args.workers, initializer=_init, initargs=(args.parser,)) as pool, \
            args.output.open("w", encoding="utf-8") as out:
        for res in pool.imap_unordered(_one, rows, chunksize=32):
            if res is None: continue
            out.write(json.dumps(res, ensure_ascii=False) + "\n"); n += 1
            if n % args.progress_every == 0: print(f"  {n}", file=sys.stderr)
    print(f"done: {n} -> {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
