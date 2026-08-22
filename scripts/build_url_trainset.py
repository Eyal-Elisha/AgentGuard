"""Extract (url, label) pairs from PhreshPhish for the URL-only classifier.

The two Stage B classifiers read visible page text. Nothing in the engine reads
the URL as a *string*: the URL rules test discrete properties (is the TLD on a
list, is there a port, does the hostname look generated). The published
baselines for this dataset all use character n-grams over the raw URL, and even
a linear model over them reaches AP 0.684 at a 1% base rate, so this is the
most obvious missing signal.

Unlike `build_semantic_trainset.py` this never parses HTML, so it is fast: only
the `url` and `label` columns are read from the parquet shards.

Domain holdout works the same way as the semantic trainset: any registered
domain appearing in `--holdout-jsonl` is dropped, so the classifier is never
fitted on a domain it will later be evaluated on. That matters more here than
anywhere else in the pipeline, because a URL model could otherwise memorise the
holdout domains outright.

Usage:
    python scripts/build_url_trainset.py \
        --parquet-glob "data/phreshphish/data/train-*.parquet" \
        --output data/url_train.jsonl \
        --holdout-jsonl data/test.jsonl --holdout-jsonl data/fresh.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_URL_CANDIDATES = ("url", "page_url", "URL", "Url")
_LABEL_CANDIDATES = ("label", "is_phish", "phish", "phishing", "y", "target")


def _pick(row: dict, candidates: tuple[str, ...]):
    for key in candidates:
        if key in row and row[key] is not None:
            return row[key]
    return None


def _norm_label(value) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return 1 if int(value) == 1 else 0
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("1", "true", "phish", "phishing", "yes"):
            return 1
        if text in ("0", "false", "benign", "legit", "legitimate", "no"):
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


def _iter_parquet(glob: str) -> Iterator[dict]:
    import pyarrow.parquet as pq

    pattern = Path(glob)
    files = sorted(pattern.parent.glob(pattern.name)) if pattern.anchor else sorted(Path().glob(glob))
    if not files:
        print(f"error: no parquet matched {glob!r}", file=sys.stderr)
        raise SystemExit(2)
    for path in files:
        print(f"  reading {path.name}", file=sys.stderr)
        table = pq.read_table(str(path))
        cols = set(table.column_names)
        url_col = next((c for c in _URL_CANDIDATES if c in cols), None)
        label_col = next((c for c in _LABEL_CANDIDATES if c in cols), None)
        if not url_col or not label_col:
            print(f"    skipped: no url/label column in {sorted(cols)}", file=sys.stderr)
            continue
        # Only these two columns are materialised, so the HTML never loads.
        for batch in table.select([url_col, label_col]).to_batches():
            for row in batch.to_pylist():
                yield {"url": row[url_col], "label": row[label_col]}


def _holdout_domains(paths: list[Path]) -> set[str]:
    domains: set[str] = set()
    for path in paths:
        if not path.exists():
            print(f"  warning: holdout file missing: {path}", file=sys.stderr)
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    dom = _registered_domain(json.loads(line).get("url", ""))
                except json.JSONDecodeError:
                    continue
                if dom:
                    domains.add(dom)
        print(f"  {path.name}: cumulative holdout domains {len(domains)}", file=sys.stderr)
    return domains


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parquet-glob", required=True)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--holdout-jsonl", action="append", default=[], type=Path,
                    help="Drop rows whose registered domain appears here (repeatable)")
    args = ap.parse_args(argv)

    holdout = _holdout_domains(args.holdout_jsonl)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    n_in = n_out = n_pos = n_holdout = n_bad = 0
    seen: set[str] = set()

    with args.output.open("w", encoding="utf-8") as out:
        for row in _iter_parquet(args.parquet_glob):
            n_in += 1
            url = row.get("url")
            label = _norm_label(row.get("label"))
            if not isinstance(url, str) or not url or label is None:
                n_bad += 1
                continue
            if holdout and _registered_domain(url) in holdout:
                n_holdout += 1
                continue
            # Exact-duplicate URLs add nothing and inflate the apparent size.
            if url in seen:
                continue
            seen.add(url)
            out.write(json.dumps({"url": url, "label": label}, ensure_ascii=False) + "\n")
            n_out += 1
            n_pos += label

    print(f"\nread {n_in} rows", file=sys.stderr)
    print(f"  dropped {n_holdout} for holdout-domain overlap", file=sys.stderr)
    print(f"  dropped {n_bad} malformed", file=sys.stderr)
    print(f"  dropped {n_in - n_holdout - n_bad - n_out} duplicate URLs", file=sys.stderr)
    print(f"kept {n_out} ({n_pos} phishing / {n_out - n_pos} benign) -> {args.output}",
          file=sys.stderr)
    return 0 if n_out else 1


if __name__ == "__main__":
    raise SystemExit(main())
