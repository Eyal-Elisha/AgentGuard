"""Convert the PhreshPhish Hugging Face dataset to the JSONL format consumed by
eval_offline.py.

PhreshPhish ships as parquet on the Hugging Face hub
(https://huggingface.co/datasets/phreshphish/phreshphish). It has two splits:

    train    498,255 rows
    test     168,060 rows

Each row contains a URL, a captured HTML body, and a phishing label. The
column names can drift between dataset revisions — this loader auto-detects
plausible candidates rather than hardcoding them.

Output is one JSON object per line:
    {"url": "...", "html": "...", "label": 0 | 1}

Usage:
    # If you already downloaded the dataset (parquet files on disk):
    python scripts/load_phreshphish.py \
        --parquet-glob "C:/path/to/phreshphish/test-*.parquet" \
        --output data/phreshphish_test.jsonl

    # Or, if you'd rather have the script pull it via `datasets`:
    python scripts/load_phreshphish.py \
        --hf-split test \
        --output data/phreshphish_test.jsonl

    # Subsample for a quick first pass:
    python scripts/load_phreshphish.py \
        --hf-split test --limit 5000 --output data/phreshphish_test_5k.jsonl

The script intentionally streams instead of loading the full dataset into RAM.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator


_URL_CANDIDATES = ("url", "page_url", "URL", "Url")
_HTML_CANDIDATES = ("html", "html_text", "raw_html", "body", "content", "page_html")
_LABEL_CANDIDATES = ("label", "is_phish", "phish", "phishing", "y", "target")


def _pick(d: dict, candidates: tuple[str, ...]) -> Any:
    for k in candidates:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _normalize_label(value: Any) -> int | None:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if int(value) == 1 else 0
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("1", "true", "phish", "phishing", "yes", "pos", "positive"):
            return 1
        if s in ("0", "false", "benign", "legit", "legitimate", "no", "neg", "negative"):
            return 0
    return None


def _iter_rows(args: argparse.Namespace) -> Iterator[dict]:
    if args.parquet_glob:
        try:
            import pyarrow.parquet as pq  # noqa: F401
        except ImportError as exc:
            print(f"error: --parquet-glob requires pyarrow ({exc})", file=sys.stderr)
            raise SystemExit(2)
        files = sorted(Path().glob(args.parquet_glob))
        if not files:
            print(f"error: no parquet files matched {args.parquet_glob!r}", file=sys.stderr)
            raise SystemExit(2)
        for f in files:
            print(f"  reading {f}", file=sys.stderr)
            table = pq.read_table(str(f))
            for batch in table.to_batches():
                for row in batch.to_pylist():
                    yield row
    else:
        try:
            from datasets import load_dataset
        except ImportError as exc:
            print(f"error: --hf-split requires the `datasets` package ({exc})", file=sys.stderr)
            raise SystemExit(2)
        print(f"  loading split={args.hf_split} from huggingface (streaming)", file=sys.stderr)
        ds = load_dataset("phreshphish/phreshphish", split=args.hf_split, streaming=True)
        for row in ds:
            yield row


def convert(rows: Iterable[dict], output: Path, limit: int | None) -> tuple[int, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    n_in = 0
    n_out = 0
    first_row_logged = False
    with output.open("w", encoding="utf-8") as f:
        for row in rows:
            n_in += 1
            if not first_row_logged:
                print(f"  first row keys: {sorted(row.keys())}", file=sys.stderr)
                first_row_logged = True

            url = _pick(row, _URL_CANDIDATES)
            html = _pick(row, _HTML_CANDIDATES)
            label = _normalize_label(_pick(row, _LABEL_CANDIDATES))

            if url is None or html is None or label is None:
                continue
            if not isinstance(url, str) or not isinstance(html, str):
                continue

            f.write(json.dumps({"url": url, "html": html, "label": label}, ensure_ascii=False) + "\n")
            n_out += 1
            if limit is not None and n_out >= limit:
                break
            if n_out and n_out % 1000 == 0:
                print(f"  wrote {n_out} rows", file=sys.stderr)
    return n_in, n_out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--parquet-glob", help="Glob for downloaded parquet shards on disk")
    src.add_argument("--hf-split", choices=["train", "test"], help="Stream from Hugging Face")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=None, help="Stop after N rows written")
    args = parser.parse_args(argv)

    rows = _iter_rows(args)
    n_in, n_out = convert(rows, args.output, args.limit)
    print(f"done: read {n_in}, wrote {n_out} -> {args.output}", file=sys.stderr)
    if n_out == 0:
        print(
            "warning: 0 rows written. The dataset column names may have drifted; "
            "edit _URL_CANDIDATES / _HTML_CANDIDATES / _LABEL_CANDIDATES at the top "
            "of this script after inspecting the first-row keys logged above.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
