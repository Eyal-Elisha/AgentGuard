"""Build a training set for the Stage B `phishing_language` classifier from
PhreshPhish, using the *same* text pipeline the classifier sees at inference.

The runtime feeds the classifier `extract_semantic_text(features)` — page title
+ visible text + stripped body + form tokens, sanitized. Training on anything
else (raw HTML, email text) is a distribution mismatch, which is exactly why
the shipped model is near-random on webpages. This script runs each PhreshPhish
row through FeatureExtractor -> extract_semantic_text and emits the two CSVs
`train.py` consumes:

    benign.csv     (text column, label 0)
    malicious.csv  (text column, label 1)

To avoid the classifier memorizing domains, pass --holdout-jsonl pointing at
the eval/test rows; any registered domain appearing there is dropped from the
training output so train and test stay domain-disjoint.

Usage:
    python scripts/build_semantic_trainset.py \
        --parquet-glob "data/phreshphish/data/train-*.parquet" \
        --out-dir data/semantic_train \
        --holdout-jsonl data/test.jsonl \
        --workers 8
"""

from __future__ import annotations

import argparse
import csv
import json
import multiprocessing
import sys
import warnings
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_URL_CANDIDATES = ("url", "page_url", "URL", "Url")
_HTML_CANDIDATES = ("html", "html_text", "raw_html", "body", "content", "page_html")
_LABEL_CANDIDATES = ("label", "is_phish", "phish", "phishing", "y", "target")

_WORKER: dict = {}


def _pick(d: dict, candidates: tuple[str, ...]):
    for k in candidates:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _norm_label(v) -> int | None:
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return 1 if int(v) == 1 else 0
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "phish", "phishing", "yes"):
            return 1
        if s in ("0", "false", "benign", "legit", "legitimate", "no"):
            return 0
    return None


def _registered_domain(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower().lstrip(".")
    except ValueError:
        return ""
    if not host:
        return ""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from publicsuffix2 import get_sld
        return get_sld(host) or host


def _worker_init(parser: str) -> None:
    warnings.filterwarnings("ignore")
    if parser != "html.parser":
        from bs4 import BeautifulSoup
        orig = BeautifulSoup.__init__

        def patched(self, markup="", features=None, *a, **k):
            if features in (None, "html.parser"):
                features = parser
            return orig(self, markup, features, *a, **k)

        BeautifulSoup.__init__ = patched

    from backend.feature_extraction.feature_extractor import FeatureExtractor
    from backend.analysis.stages.stage_b.sanitization import extract_semantic_text
    _WORKER["extract"] = FeatureExtractor()
    _WORKER["semantic"] = extract_semantic_text


def _process(row: dict) -> tuple[str, int] | None:
    url = _pick(row, _URL_CANDIDATES)
    html = _pick(row, _HTML_CANDIDATES)
    label = _norm_label(_pick(row, _LABEL_CANDIDATES))
    if not isinstance(url, str) or not isinstance(html, str) or label is None:
        return None
    try:
        body = html.encode("utf-8", errors="ignore")
        features = _WORKER["extract"].extract(
            url=url, method="GET", headers={"Content-Type": "text/html"}, body=body)
        text = _WORKER["semantic"](features)
    except Exception:
        return None
    text = " ".join(text.split())
    if len(text) < 32:
        return None
    return text, label


def _iter_parquet(glob: str) -> Iterator[dict]:
    import pyarrow.parquet as pq
    gp = Path(glob)
    files = sorted(gp.parent.glob(gp.name)) if gp.anchor else sorted(Path().glob(glob))
    if not files:
        print(f"error: no parquet matched {glob!r}", file=sys.stderr)
        raise SystemExit(2)
    for f in files:
        print(f"  reading {f}", file=sys.stderr)
        for batch in pq.read_table(str(f)).to_batches():
            yield from batch.to_pylist()


def _iter_jsonl(path: Path) -> Iterator[dict]:
    """Same records, from a JSONL corpus instead of parquet.

    Lets a second corpus be folded into the training mix. Single-corpus
    training scores far better on its own corpus than on anyone else's, so
    mixing corpora is the lever that actually moves cross-corpus numbers.
    """
    print(f"  reading {path}", file=sys.stderr)
    with path.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"    skipping line {i}: {exc}", file=sys.stderr)


def _load_holdout_domains(path: Path | None) -> set[str]:
    if not path or not path.exists():
        return set()
    import json
    doms = set()
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = _registered_domain(json.loads(line).get("url", ""))
                if d:
                    doms.add(d)
            except json.JSONDecodeError:
                continue
    print(f"  holdout domains to exclude: {len(doms)}", file=sys.stderr)
    return doms


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--parquet-glob", help="PhreshPhish parquet shards")
    ap.add_argument("--input-jsonl", action="append", default=[], type=Path,
                    help="Additional {url, html, label} JSONL corpus (repeatable). "
                         "Combine with --parquet-glob to train across corpora.")
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--append", action="store_true",
                    help="Append to existing CSVs instead of overwriting them")
    ap.add_argument("--holdout-jsonl", type=Path,
                    help="Drop rows whose registered domain appears in this JSONL")
    ap.add_argument("--workers", type=int, default=multiprocessing.cpu_count())
    ap.add_argument("--parser", choices=["lxml", "html.parser"], default="lxml")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--progress-every", type=int, default=2000)
    args = ap.parse_args(argv)

    if not args.parquet_glob and not args.input_jsonl:
        ap.error("pass --parquet-glob, --input-jsonl, or both")

    holdout = _load_holdout_domains(args.holdout_jsonl)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    benign_path = args.out_dir / "benign.csv"
    malicious_path = args.out_dir / "malicious.csv"

    # Appending lets a second corpus be added to an existing trainset without
    # reprocessing the first; the header only belongs on a fresh file.
    _mode = "a" if args.append else "w"
    _write_header = not (args.append and benign_path.exists())

    n_in = n_out = n_pos = n_drop_holdout = 0
    ctx = multiprocessing.get_context("spawn")

    def _sources():
        if args.parquet_glob:
            yield from _iter_parquet(args.parquet_glob)
        for path in args.input_jsonl:
            yield from _iter_jsonl(path)

    def _rows():
        nonlocal n_drop_holdout
        for row in _sources():
            if holdout:
                dom = _registered_domain(_pick(row, _URL_CANDIDATES) or "")
                if dom and dom in holdout:
                    n_drop_holdout += 1
                    continue
            yield row

    with ctx.Pool(args.workers, initializer=_worker_init, initargs=(args.parser,)) as pool, \
            benign_path.open(_mode, encoding="utf-8", newline="") as bf, \
            malicious_path.open(_mode, encoding="utf-8", newline="") as mf:
        bw = csv.writer(bf); mw = csv.writer(mf)
        if _write_header:
            bw.writerow(["text"]); mw.writerow(["text"])
        for res in pool.imap_unordered(_process, _rows(), chunksize=16):
            n_in += 1
            if res is not None:
                text, label = res
                (mw if label == 1 else bw).writerow([text])
                n_out += 1
                n_pos += label
            if args.progress_every and n_in % args.progress_every == 0:
                print(f"  processed {n_in}  kept {n_out} (pos={n_pos})", file=sys.stderr)
            if args.limit and n_out >= args.limit:
                break

    print(f"done: read {n_in}, kept {n_out} (malicious={n_pos}, benign={n_out - n_pos}), "
          f"dropped {n_drop_holdout} holdout-domain rows", file=sys.stderr)
    print(f"  -> {benign_path}\n  -> {malicious_path}", file=sys.stderr)
    return 0 if n_out else 1


if __name__ == "__main__":
    raise SystemExit(main())
