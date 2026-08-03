"""Split a JSONL of {url, html, label} into dev/test partitions that are
disjoint by *registered domain* (eTLD+1).

Calibrating thresholds on rows whose domain also appears in the test split
leaks — a rule that memorizes a domain looks better than it is. This assigns
each registered domain wholesale to one side via a stable hash, so no domain
straddles the split, and reports the label balance of each side.

Usage:
    python scripts/split_by_domain.py --input data/phreshphish_test_30k.jsonl \
        --dev data/dev.jsonl --test data/test.jsonl --dev-frac 0.5
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import warnings
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


def _registered_domain(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        host = ""
    host = host.lower().lstrip(".")
    if not host:
        return ""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from publicsuffix2 import get_sld
        return get_sld(host) or host


def _bucket(domain: str, dev_frac: float) -> str:
    """Stable per-domain assignment: hash to [0,1), compare to dev_frac."""
    h = hashlib.sha256(domain.encode("utf-8")).hexdigest()
    frac = int(h[:8], 16) / 0xFFFFFFFF
    return "dev" if frac < dev_frac else "test"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--dev", required=True, type=Path)
    ap.add_argument("--test", required=True, type=Path)
    ap.add_argument("--dev-frac", type=float, default=0.5,
                    help="Approx fraction of *domains* going to dev (default 0.5)")
    args = ap.parse_args(argv)

    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2

    args.dev.parent.mkdir(parents=True, exist_ok=True)
    counts = {"dev": Counter(), "test": Counter()}
    domains = {"dev": set(), "test": set()}

    with args.input.open("r", encoding="utf-8") as fin, \
            args.dev.open("w", encoding="utf-8") as fdev, \
            args.test.open("w", encoding="utf-8") as ftest:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            dom = _registered_domain(rec.get("url", ""))
            side = _bucket(dom, args.dev_frac) if dom else "test"
            (fdev if side == "dev" else ftest).write(
                json.dumps(rec, ensure_ascii=False) + "\n")
            counts[side][rec.get("label")] += 1
            if dom:
                domains[side].add(dom)

    overlap = domains["dev"] & domains["test"]
    for side in ("dev", "test"):
        c = counts[side]
        n = sum(c.values())
        pos = c.get(1, 0)
        print(f"{side:4}: {n:6} rows  phish={pos:5}  benign={c.get(0,0):5}  "
              f"domains={len(domains[side]):5}")
    print(f"domain overlap between dev and test: {len(overlap)} (must be 0)")
    return 0 if not overlap else 1


if __name__ == "__main__":
    raise SystemExit(main())
