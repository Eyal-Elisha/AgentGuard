"""Convert the Kaggle phishing-HTML datasets into our {url, html, label} JSONL.

These are the only genuinely independent page corpora available to the project.
PhreshPhish is what everything was tuned on, ealvaradob is half in training, and
the HuggingFace candidate that looked like a third corpus turned out to be a
byte-identical re-upload of ealvaradob. These two are separate collections, so
scoring the unchanged engine on them gives the first generalisation number that
needs no caveat.

A naming asymmetry has to be handled or the result is worthless.

`huntingdata11` names its benign files after the site (`0_adyen_com.html`) and
its phishing files by serial number (`7453961.html`): 98% of benign carry a
domain, 0% of phishing do. Reconstructing URLs from those names would hand
every benign page a reputable hostname and every phishing page nothing, so the
URL rules would separate the classes on file naming rather than on phishing.
This loader therefore blanks the URL for *both* classes there, making it a
content-only corpus in the same way ealvaradob is.

`zackyzac` names both classes after the site (`abctpia-gid.com_77.txt`,
`123people.com_141.txt`), so URLs are reconstructed and the URL rules can be
measured on independent data for the first time. The reconstruction gives
scheme and host only, so path-based signals are absent, and https is assumed,
which means the unencrypted-connection rule cannot fire.

Usage:
    python scripts/load_kaggle_html.py --dataset zackyzac --output data/kaggle_zackyzac.jsonl
    python scripts/load_kaggle_html.py --dataset huntingdata11 --output data/kaggle_hunting.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# dataset -> (root, [(subdir_glob, label)], reconstruct_urls)
LAYOUTS = {
    "huntingdata11": {
        "root": Path("data/kaggle/huntingdata11"),
        "dirs": [
            ("training/NotPhish", 0), ("training/Phish", 1),
            ("validation/NotPhish", 0), ("validation/Phish", 1),
        ],
        "urls": False,   # see module docstring: naming is asymmetric by class
    },
    "zackyzac": {
        "root": Path("data/kaggle/zackyzac/html_content"),
        "dirs": [("genuine_site_0", 0), ("phishing_site_1", 1)],
        "urls": True,
    },
}

_TRAILING_INDEX = re.compile(r"_\d+$")
_LEADING_INDEX = re.compile(r"^\d+_")
_CLASS_PREFIX = re.compile(r"^(?:genuine|phishing)_", re.I)

_TLDS: set[str] | None = None


def _tlds() -> set[str]:
    global _TLDS
    if _TLDS is None:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from publicsuffix2 import PublicSuffixList
        _TLDS = {t.lstrip("*.!").lower() for t in PublicSuffixList().tlds}
    return _TLDS


def _domain_from_name(stem: str) -> str:
    """Recover a hostname from a filename.

    Two shapes appear. Simple: `abctpia-gid.com_77`, host then an index.
    Awkward: `genuine_ehow.comlist_6137088_list-alpha.html`, which is the class,
    then the host with the *path separators removed*, so the TLD runs straight
    into the first path segment and there is no delimiter to split on.

    The host is recovered by finding where a valid TLD ends. Every label is
    tested for the longest public-suffix prefix it starts with, and the longest
    match across the whole name wins: in `www.aurigane.comimagesstories` the
    label `aurigane` starts with the ccTLD `au`, but `comimagesstories` starts
    with `com`, and preferring the longer match gives `www.aurigane.com` rather
    than `www.au`.
    """
    stem = _CLASS_PREFIX.sub("", stem)
    stem = _LEADING_INDEX.sub("", stem)
    stem = _TRAILING_INDEX.sub("", stem)
    # The host cannot contain "_", so it lies within the first underscore-free run.
    stem = stem.split("_")[0].lower().strip(".")
    if "." not in stem:            # `0_adyen_com` style, underscores were dots
        return ""

    labels = stem.split(".")
    tlds = _tlds()

    # A label that is entirely a TLD is a real domain boundary, so those win.
    # Take the rightmost, or `austinheights.edu.my` stops at the `.edu`.
    full = [i for i in range(1, len(labels)) if labels[i] in tlds]
    if full:
        best_host = ".".join(labels[: full[-1] + 1])
    else:
        # No clean boundary: the TLD has run into the path. Take the longest
        # public-suffix prefix found anywhere, so `comimagesstories` (com) beats
        # `aurigane` (au).
        best_host, best_len = "", 0
        for i in range(1, len(labels)):
            label = labels[i]
            for cut in range(len(label), 1, -1):
                if label[:cut] in tlds:
                    if cut > best_len:
                        best_len = cut
                        best_host = ".".join(labels[:i]) + "." + label[:cut]
                    break                  # longest prefix at this position
    if not best_host:
        return ""
    if not re.fullmatch(r"[a-z0-9.\-]+\.[a-z]{2,}", best_host):
        return ""
    return best_host


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", required=True, choices=sorted(LAYOUTS))
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--min-chars", type=int, default=200,
                    help="Skip files with less markup than this")
    args = ap.parse_args(argv)

    spec = LAYOUTS[args.dataset]
    root: Path = spec["root"]
    if not root.exists():
        print(f"error: {root} not found - download the dataset first", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    n_out = n_pos = n_skip = n_nodomain = 0

    with args.output.open("w", encoding="utf-8") as out:
        for subdir, label in spec["dirs"]:
            folder = root / subdir
            if not folder.is_dir():
                print(f"  warning: missing {folder}", file=sys.stderr)
                continue
            count = 0
            for path in sorted(folder.iterdir()):
                if not path.is_file():
                    continue
                try:
                    html = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    n_skip += 1
                    continue
                if len(html) < args.min_chars:
                    n_skip += 1
                    continue

                url = ""
                if spec["urls"]:
                    domain = _domain_from_name(path.stem)
                    if not domain:
                        n_nodomain += 1
                    else:
                        url = f"https://{domain}/"

                out.write(json.dumps(
                    {"url": url, "html": html, "label": label}, ensure_ascii=False) + "\n")
                n_out += 1
                n_pos += label
                count += 1
            print(f"  {subdir:<24} {count} pages (label={label})", file=sys.stderr)

    print(f"\nwrote {n_out} pages ({n_pos} phishing / {n_out - n_pos} benign, "
          f"base rate {n_pos/max(n_out,1):.1%}) -> {args.output}", file=sys.stderr)
    if not spec["urls"]:
        print("  URLs blanked for both classes: this corpus names the classes "
              "differently, so URL rules would separate them on filenames.",
              file=sys.stderr)
    if n_nodomain:
        print(f"  {n_nodomain} files had no recoverable domain", file=sys.stderr)
    if n_skip:
        print(f"  skipped {n_skip} files under {args.min_chars} chars", file=sys.stderr)
    return 0 if n_out else 1


if __name__ == "__main__":
    raise SystemExit(main())
