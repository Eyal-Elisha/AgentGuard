"""The demonstration set: four hand-written pages, and the engine's verdict on each.

Two earlier attempts at this are worth knowing about, because both produced a
demo that looked convincing and proved nothing.

Serving pages from `http://127.0.0.1:8777/` fails because half the rules read the
URL. Measured over 400 corpus pages that arrangement flagged 219/219 phishing
*and* 181/181 benign: `ip_based_url` and `non_standard_port` fire on every
request, so it blocks everything for reasons that have nothing to do with the
page. Tunnelling through ngrok fails the other way: the rules then see
`<id>.ngrok-free.app`, a perfectly ordinary domain, and a real phishing page
scores 0.18 and is allowed.

The URL has to look like what it claims to be. So each page here is bound to a
hostname, that name is pointed at this machine through the hosts file, and the
page is served on port 80 — one of the standard ports, so the URL carries no port
and `non_standard_port` stays quiet. Every rule that fires then fires for a
reason worth explaining out loud.

The pages are written by hand. Nothing is captured from a real attacker, there is
no JavaScript, and no request leaves the machine: the forms point at hosts that
do not resolve. That is deliberate. An earlier version of this script shipped
real captured phishing markup, and a teammate rendered one in a browser.

    python scripts/demo_live.py                 # verdicts, no setup needed
    python scripts/demo_live.py --serve         # live, through the proxy
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, List

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

PAGES_DIR = _REPO / "demo_pages"
GREEN, YELLOW, RED, DIM, BOLD, RESET = (
    "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[1m", "\033[0m")
_COLOUR = {"allow": GREEN, "warn": YELLOW, "block": RED}


def load_manifest() -> List[Dict]:
    manifest = json.loads((PAGES_DIR / "pages.json").read_text(encoding="utf-8"))
    for page in manifest["pages"]:
        page["html"] = (PAGES_DIR / page["file"]).read_text(encoding="utf-8")
        # https, because that is what these pages would really be served over
        # and it keeps unencrypted_connection out of the demo. Live --serve is
        # plain http, so that rule fires there as well and the scores sit higher.
        page["url"] = f"https://{page['host']}/"
    return manifest["pages"]


def build_engine():
    warnings.filterwarnings("ignore")
    from backend.analysis.stages.stage_a import blacklist as bl

    # Matches the offline harness: no rule here should depend on a live feed.
    bl.blacklist_cache.is_listed = lambda domain: (False, "offline")

    from backend.analysis.scoring import meta_classifier as meta
    from backend.analysis.scoring.floors import apply_decision_floors
    from backend.analysis.stages.stage_a import StageAEvaluator
    from backend.analysis.stages.stage_b import StageBEvaluator
    from backend.feature_extraction.feature_extractor import FeatureExtractor

    return (FeatureExtractor(), StageAEvaluator(), StageBEvaluator(),
            meta, apply_decision_floors)


def judge(engine, url: str, html: str):
    """One page down the same path the proxy uses."""
    extractor, stage_a, stage_b, meta, floors = engine
    started = time.perf_counter()
    features = extractor.extract(url=url, method="GET",
                                 headers={"content-type": "text/html"}, body=html)
    result = stage_a.evaluate(features)
    rule_results = list(result.rule_results)
    if not result.hard_block_triggered:
        rule_results += list(stage_b.evaluate(features))

    risk = meta.score(rule_results)
    decision = meta.decide(risk) if risk is not None else result.decision
    # The floor is why the injection page warns: no combiner would raise it on
    # a phishing score, because it is not a phishing page.
    decision = floors(decision, rule_results)

    elapsed = (time.perf_counter() - started) * 1000
    fired = sorted(((r.rule_id, r.score) for r in rule_results
                    if r.score and r.score > 0.30), key=lambda kv: -kv[1])
    return decision.value, (risk if risk is not None else result.risk_score), fired, elapsed


def serve(pages: List[Dict], port: int) -> None:
    """Answer on each page's own hostname, so the proxy sees a realistic URL."""
    from http.server import BaseHTTPRequestHandler, HTTPServer

    by_host = {page["host"]: page for page in pages}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            host = self.headers.get("Host", "").split(":")[0]
            page = by_host.get(host)
            if page is None:
                body = b"<h1>Not one of the demo hostnames</h1>"
                self.send_response(404)
            else:
                body = page["html"].encode("utf-8")
                self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            print("   served", self.headers.get("Host", "?"), file=sys.stderr)

    print()
    print(f"{BOLD}  1. Add these to your hosts file, as administrator{RESET}")
    print(r"        C:\Windows\System32\drivers\etc\hosts     (Windows)")
    print("        /etc/hosts                                (macOS, Linux)")
    print()
    for host in by_host:
        print(f"        127.0.0.1  {host}")
    print()
    print(f"{BOLD}  2. Browse to these, through the proxy{RESET}")
    for host, page in by_host.items():
        suffix = "" if port == 80 else f":{port}"
        print(f"        {page['expect'].upper():<6} http://{host}{suffix}/")
    print()
    print(f"{BOLD}  3. Remove the hosts lines when you are finished{RESET}")
    print()

    try:
        HTTPServer(("127.0.0.1", port), Handler).serve_forever()
    except PermissionError:
        print(f"  cannot bind port {port}. Run as administrator, or pass --serve 8080 "
              f"and browse to http://<host>:8080/ instead.", file=sys.stderr)


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--serve", type=int, nargs="?", const=80, metavar="PORT",
                    help="serve the pages for a live run through the proxy (default port 80)")
    args = ap.parse_args(argv)

    pages = load_manifest()
    if args.serve:
        serve(pages, args.serve)
        return 0

    engine = build_engine()
    print(f"\n  {len(pages)} hand-written pages, through the live engine\n")
    agreed = 0
    for page in pages:
        verdict, risk, fired, ms = judge(engine, page["url"], page["html"])
        ok = verdict == page["expect"]
        agreed += ok
        colour = _COLOUR.get(verdict, "")
        print(f"  {page['url']}")
        print(f"     {colour}{BOLD}{verdict.upper():<6}{RESET}  risk {risk:.2f}"
              f"   {ms:.0f} ms" + ("" if ok else f"   {RED}expected {page['expect']}{RESET}"))
        for rule_id, score in fired:
            print(f"        {DIM}{rule_id:<24}{score:.2f}{RESET}")
        if not fired:
            print(f"        {DIM}no rule fired{RESET}")
        print(f"        {DIM}{page['why']}{RESET}")
        print()

    print(f"  {agreed}/{len(pages)} pages behaved as documented")
    return 0 if agreed == len(pages) else 1


if __name__ == "__main__":
    raise SystemExit(main())
