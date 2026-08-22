"""Quick manual tester: run URLs through the URL-only rules and show what fires.

Prints each rule's verdict and explanation for the URLs given, which is the
fastest way to answer "why is this domain flagged?". Pass one or more URLs, or
none to use the built-in samples:

    python scripts/try_domain.py https://e7rmtin3r4b.com https://fox13memphis.com

Only the six rules that decide from the URL alone. Anything needing page
content — brand mismatch, forms, the semantic rules — is not covered here; use
`eval_offline.py` for the full pipeline.
"""
from __future__ import annotations
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import warnings
warnings.simplefilter("ignore")
from backend.feature_extraction.feature_extractor import FeatureExtractor
from backend.analysis.stages.stage_a.deterministic_rules import (
    rule_algorithmic_domain, rule_non_standard_port, rule_suspicious_tld,
    rule_typosquatting, rule_ip_based_url, rule_unencrypted_connection,
)

_RULES = [
    ("algorithmic_domain", rule_algorithmic_domain),
    ("non_standard_port", rule_non_standard_port),
    ("suspicious_tld", rule_suspicious_tld),
    ("typosquatting", rule_typosquatting),
    ("ip_based_url", rule_ip_based_url),
    ("unencrypted_connection", rule_unencrypted_connection),
]


def main(argv):
    urls = argv or [
        "https://e7rmtin3r4b.com/verify",   # DGA phish -> algorithmic_domain fires
        "https://fox13memphis.com/",         # legit news -> algorithmic_domain (false positive)
        "https://shop24.com/",               # word+number -> should NOT fire
        "https://www.google.com/",           # clean
        "https://paypa1.tk:8443/login",      # typosquat + odd port + bad TLD
    ]
    ex = FeatureExtractor()
    for url in urls:
        f = ex.extract(url=url, method="GET", headers={"Content-Type": "text/html"}, body=b"<html></html>")
        fired = []
        for name, fn in _RULES:
            score, why = fn(f)
            if score and score > 0:
                fired.append(f"{name} ({why})")
        print(f"\n{url}")
        if fired:
            for x in fired:
                print(f"   FIRES: {x}")
        else:
            print("   (no URL rules fire)")


if __name__ == "__main__":
    main(sys.argv[1:])
