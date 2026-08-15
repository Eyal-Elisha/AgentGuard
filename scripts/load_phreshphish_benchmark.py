"""Assemble PhreshPhish's official benchmark sets at their published base rates.

Chapter 4 compares AgentGuard against the baselines the dataset authors report,
but until now that comparison was approximate: our held-out pages were
re-sampled to each base rate ourselves. The dataset ships the actual benchmark
membership lists, so the comparison can be exact instead.

Each `benchmark/benchmark-<rate>/<i>.txt` is a list of phishing sha256 ids, and
`benchmark/benign.txt` is the shared benign pool. A benchmark instance is one
phishing list plus the benign pool, which lands on the intended base rate:
911 phishing against 90,270 benign is 1.00%.

Leakage matters here and is easy to miss. Our dev split was drawn from the same
PhreshPhish test split, and the meta-classifier was fitted on it, so some
benchmark rows may be rows the combiner has already seen. `--exclude-jsonl`
drops them, and the counts are reported either way so the size of the problem
is visible rather than assumed.

Usage:
    python scripts/load_phreshphish_benchmark.py --rate 100 --instance 0 \
        --parquet-glob "data/phreshphish/data/test-*.parquet" \
        --exclude-jsonl data/dev.jsonl \
        --output data/benchmark_100_0.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

_REPO = "https://huggingface.co/datasets/phreshphish/phreshphish/resolve/main/"
RATES = {"005": 0.05, "010": 0.10, "050": 0.50, "100": 1.00, "500": 5.00}


def _fetch(rel_path: str, cache_dir: Path) -> list[str]:
    """Read a benchmark id list, caching it so repeat runs are offline."""
    cached = cache_dir / rel_path.replace("/", "_")
    if cached.exists():
        return cached.read_text(encoding="utf-8").split()
    cache_dir.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(_REPO + rel_path, timeout=60) as resp:
        body = resp.read().decode("utf-8", "ignore")
    cached.write_text(body, encoding="utf-8")
    return body.split()


def _excluded_keys(paths: list[Path]) -> tuple[set[str], set[str]]:
    """Rows to drop, keyed by sha256 and by URL.

    Our own splits were written before the sha256 column was being carried, so
    they identify rows only by URL. Both keys are collected and either one
    matching is enough to drop a row.
    """
    shas: set[str] = set()
    urls: set[str] = set()
    for path in paths:
        if not path.exists():
            print(f"  warning: exclude file missing: {path}", file=sys.stderr)
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("sha256"):
                    shas.add(rec["sha256"])
                if rec.get("url"):
                    urls.add(rec["url"])
    return shas, urls


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rate", required=True, choices=sorted(RATES),
                    help="Base rate directory: 005=0.05%%, 100=1%%, 500=5%%")
    ap.add_argument("--instance", type=int, default=0,
                    help="Which benchmark instance (the authors average over many)")
    ap.add_argument("--parquet-glob", default="data/phreshphish/data/test-*.parquet")
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--exclude-jsonl", action="append", default=[], type=Path,
                    help="Drop rows whose sha256 appears here (repeatable)")
    ap.add_argument("--cache-dir", type=Path, default=Path("data/benchmark_ids"))
    ap.add_argument("--with-html", action="store_true",
                    help="Materialise page HTML as well. A 1%% benchmark is ~91k pages "
                         "and runs to tens of GB; by default only the index is written "
                         "and scorers stream the HTML from the parquet shards.")
    args = ap.parse_args(argv)

    phish_ids = set(_fetch(f"benchmark/benchmark-{args.rate}/{args.instance}.txt", args.cache_dir))
    benign_ids = set(_fetch("benchmark/benign.txt", args.cache_dir))
    wanted = phish_ids | benign_ids
    print(f"benchmark-{args.rate} instance {args.instance}: "
          f"{len(phish_ids)} phishing + {len(benign_ids)} benign "
          f"= {len(phish_ids)/(len(phish_ids)+len(benign_ids)):.2%} base rate",
          file=sys.stderr)

    excl_sha, excl_url = _excluded_keys(args.exclude_jsonl)
    wanted -= excl_sha
    if excl_sha or excl_url:
        print(f"  exclusion set: {len(excl_sha)} sha256, {len(excl_url)} urls",
              file=sys.stderr)

    import pyarrow.parquet as pq
    columns = ["sha256", "url", "label"] + (["html"] if args.with_html else [])
    pattern = Path(args.parquet_glob)
    files = sorted(pattern.parent.glob(pattern.name))
    if not files:
        print(f"error: no parquet matched {args.parquet_glob!r}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    n_out = n_pos = n_dropped = 0
    with args.output.open("w", encoding="utf-8") as out:
        for path in files:
            table = pq.read_table(str(path), columns=columns)
            for row in table.to_pylist():
                sha = row.get("sha256")
                if sha not in wanted:
                    continue
                if (row.get("url") or "") in excl_url:
                    n_dropped += 1
                    continue
                label = 1 if str(row.get("label", "")).strip().lower() in (
                    "1", "phish", "phishing", "true") else 0
                record = {"sha256": sha, "url": row.get("url") or "", "label": label}
                if args.with_html:
                    record["html"] = row.get("html") or ""
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                n_out += 1
                n_pos += label

    rate = n_pos / n_out if n_out else 0.0
    if n_dropped:
        print(f"  dropped {n_dropped} benchmark rows our models had already seen "
              f"({n_dropped/(n_out+n_dropped):.2%} of the benchmark)", file=sys.stderr)
    print(f"wrote {n_out} rows ({n_pos} phishing / {n_out - n_pos} benign, "
          f"base rate {rate:.3%}) -> {args.output}", file=sys.stderr)
    unresolved = len(wanted) - n_out - n_dropped
    if unresolved > 0:
        print(f"  note: {unresolved} ids were not present in the parquet shards",
              file=sys.stderr)
    return 0 if n_out else 1


if __name__ == "__main__":
    raise SystemExit(main())
