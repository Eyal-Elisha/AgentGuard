from __future__ import annotations

from pathlib import Path

from mitmproxy import http

from backend.analysis.rules import EvaluationResult
from backend.analysis.stages.stage_a import StageAEvaluator
from backend.analysis.stages.stage_a.deterministic_rules import custom_blacklist_entry_matches
from backend.analysis.stages.stage_a.helpers import strip_www
from backend.feature_extraction.feature_extractor import FeatureExtractor

_PROXY_DIR = Path(__file__).resolve().parent
_DEFAULT_BLACKLIST_FILENAME = "custom_blacklist.txt"


def parse_custom_blacklist_file_content(content: str) -> frozenset[str]:
    """One entry per line; # starts a comment; entries are lowercased."""
    entries: list[str] = []
    for line in content.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            entries.append(line.lower())
    return frozenset(entries)


def custom_blacklist_file_path() -> Path:
    return _PROXY_DIR / _DEFAULT_BLACKLIST_FILENAME


def load_custom_blacklist_file(path: Path) -> frozenset[str]:
    if not path.is_file():
        return frozenset()
    text = path.read_text(encoding="utf-8")
    return parse_custom_blacklist_file_content(text)


_CUSTOM_BLACKLIST = load_custom_blacklist_file(custom_blacklist_file_path())


def flow_matches_custom_blacklist(flow: http.HTTPFlow) -> bool:
    """True if host/URL matches the file-backed custom list (same rules as Stage A rule 9)."""
    if not _CUSTOM_BLACKLIST:
        return False
    host_stripped = strip_www(flow.request.host)
    url_lc = flow.request.pretty_url.lower()
    for entry in _CUSTOM_BLACKLIST:
        if custom_blacklist_entry_matches(entry, host_stripped=host_stripped, url_lc=url_lc):
            return True
    return False


_extractor = FeatureExtractor()
_evaluator = StageAEvaluator(custom_blacklist=_CUSTOM_BLACKLIST)


def evaluate_http_payload(
    *,
    url: str,
    method: str,
    headers: dict,
    body: bytes | str,
) -> EvaluationResult:
    features = _extractor.extract(
        url=url,
        method=method,
        headers=headers,
        body=body,
    )
    return _evaluator.evaluate(features)
