"""Run the real engine over real captured pages, in front of an audience.

The pages in `demo_pages/` were written to trip the rules, so they demonstrate
nothing. Replaying corpus pages over a local web server is worse: half the rules
read the URL, and a page served from `http://127.0.0.1:8777/` trips
`ip_based_url` and `non_standard_port` on every request. Measured over 400
PhreshPhish pages, that setup flags 219/219 phishing *and* 181/181 benign — a
100% false-positive rate dressed up as perfect detection.

So this does not serve anything. It takes real captured pages, keeps their real
URLs, and runs them through the same Stage A, Stage B and meta-classifier the
proxy calls, printing what each rule concluded. That is a demonstration of the
engine rather than of a mock-up.

    python scripts/demo_live.py --count 12
    python scripts/demo_live.py --count 40 --only-caught     # for a short slot

Reputation lookups are disabled, matching the offline harness, so nothing here
depends on a live feed.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, List

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

GREEN, YELLOW, RED, DIM, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"
_COLOUR = {"allow": GREEN, "warn": YELLOW, "block": RED}


def load_pages(path: Path, count: int, seed: int, max_bytes: int) -> List[Dict]:
    """Half phishing, half benign, taken from the head of a corpus file."""
    want = max(count // 2, 1)
    phishing: List[Dict] = []
    benign: List[Dict] = []
    with path.open(encoding="utf-8") as fh:
        for scanned, line in enumerate(fh):
            if scanned > 40_000 or (len(phishing) >= want * 5 and len(benign) >= want * 5):
                break
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not row.get("html") or not row.get("url"):
                continue
            if len(row["html"]) > max_bytes:
                continue
            (phishing if row.get("label") == 1 else benign).append(row)
    rng = random.Random(seed)
    rng.shuffle(phishing)
    rng.shuffle(benign)
    picked = phishing[:want] + benign[:want]
    rng.shuffle(picked)
    return picked


def build_engine():
    warnings.filterwarnings("ignore")
    from backend.analysis.stages.stage_a import blacklist as bl

    # Same choice the offline harness makes: a feed queried today says nothing
    # about a page captured months ago, and the demo should not need network.
    bl.blacklist_cache.is_listed = lambda domain: (False, "offline")

    from backend.analysis.scoring import meta_classifier as meta
    from backend.analysis.stages.stage_a import StageAEvaluator
    from backend.analysis.stages.stage_b import StageBEvaluator
    from backend.feature_extraction.feature_extractor import FeatureExtractor

    return FeatureExtractor(), StageAEvaluator(), StageBEvaluator(), meta


def judge(engine, url: str, html: str):
    """One page through the real path. Returns (verdict, risk, rules, milliseconds)."""
    extractor, stage_a, stage_b, meta = engine
    started = time.perf_counter()
    features = extractor.extract(url=url, method="GET",
                                 headers={"content-type": "text/html"}, body=html)
    result = stage_a.evaluate(features)
    rule_results = list(result.rule_results)
    if result.stage_b_required:
        rule_results += list(stage_b.evaluate(features))
    risk = meta.score(rule_results)
    verdict = (meta.decide(risk) if risk is not None else result.decision).value
    elapsed = (time.perf_counter() - started) * 1000
    fired = [(r.rule_id, r.score) for r in rule_results if r.score and r.score > 0.30]
    fired.sort(key=lambda kv: -kv[1])
    return verdict, (risk if risk is not None else result.risk_score), fired, elapsed


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=Path("data/phreshphish_test_30k.jsonl"),
                    help="corpus JSONL of {url, html, label} with REAL urls")
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--max-kb", type=int, default=400)
    ap.add_argument("--only-caught", action="store_true",
                    help="show only the phishing pages that were acted on")
    args = ap.parse_args(argv)

    if not args.input.exists():
        print(f"error: {args.input} not found", file=sys.stderr)
        return 1

    pages = load_pages(args.input, args.count, args.seed, args.max_kb * 1024)
    if not pages:
        print("error: no usable pages in that file", file=sys.stderr)
        return 1

    engine = build_engine()
    caught = missed = false_alarm = correct_pass = 0
    times: List[float] = []

    print(f"\n  {len(pages)} real captured pages, real URLs, through the live engine\n")
    for page in pages:
        verdict, risk, fired, ms = judge(engine, page["url"], page["html"])
        times.append(ms)
        is_phishing = page.get("label") == 1
        acted = verdict in ("warn", "block")
        if is_phishing and acted:
            caught += 1
        elif is_phishing:
            missed += 1
        elif acted:
            false_alarm += 1
        else:
            correct_pass += 1

        if args.only_caught and not (is_phishing and acted):
            continue

        truth = f"{RED}PHISHING{RESET}" if is_phishing else f"{DIM}legitimate{RESET}"
        colour = _COLOUR.get(verdict, "")
        print(f"  {page['url'][:62]:<62}")
        print(f"     truth {truth}   risk {risk:.2f}   "
              f"{colour}{verdict.upper()}{RESET}   {ms:.0f} ms")
        if fired:
            for rule_id, score in fired[:4]:
                print(f"        {DIM}{rule_id:<26}{score:.2f}{RESET}")
        else:
            print(f"        {DIM}no rule fired{RESET}")
        print()

    total_phishing = caught + missed
    total_benign = false_alarm + correct_pass
    print("  " + "-" * 62)
    print(f"  caught {caught}/{total_phishing} phishing"
          f"   false alarms {false_alarm}/{total_benign} legitimate"
          f"   median {sorted(times)[len(times)//2]:.0f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
