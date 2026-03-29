from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.analysis.stages.stage_a.deterministic_rules import custom_blacklist_entry_matches

from backend.proxy.policy_engine import (
    custom_blacklist_file_path,
    flow_matches_custom_blacklist,
    load_custom_blacklist_file,
    parse_custom_blacklist_file_content,
)

def test_parse_blacklist_file_skips_comments_and_blank_lines():
    text = """
# full line comment
  Bad.EXAMPLE.com

  https://X.Y/z  # tail comment
"""
    assert parse_custom_blacklist_file_content(text) == frozenset(
        {"bad.example.com", "https://x.y/z"}
    )


def test_load_custom_blacklist_file_missing_returns_empty(tmp_path: Path):
    assert load_custom_blacklist_file(tmp_path / "nope.txt") == frozenset()


def test_load_custom_blacklist_file_reads_file(tmp_path: Path):
    p = tmp_path / "bl.txt"
    p.write_text("one.com\ntwo.org\n", encoding="utf-8")
    assert load_custom_blacklist_file(p) == frozenset({"one.com", "two.org"})


def test_custom_blacklist_file_path_uses_default_policy_file():
    path = custom_blacklist_file_path()
    assert path.name == "custom_blacklist.txt"


def test_custom_blacklist_entry_matches_exact_url_with_query():
    assert (
        custom_blacklist_entry_matches(
            "https://example.com/login",
            host_stripped="example.com",
            url_lc="https://example.com/login?next=%2Fhome",
        )
        is True
    )


def test_custom_blacklist_entry_matches_trailing_slash_url_with_query():
    assert (
        custom_blacklist_entry_matches(
            "https://example.com/login/",
            host_stripped="example.com",
            url_lc="https://example.com/login/?next=%2Fhome",
        )
        is True
    )


def test_flow_matches_custom_blacklist_for_subdomain():
    flow = SimpleNamespace(
        request=SimpleNamespace(
            host="www.youtube.com",
            pretty_url="https://www.youtube.com/watch?v=123",
        )
    )
    with patch(
        "backend.proxy.policy_engine._CUSTOM_BLACKLIST",
        frozenset({"youtube.com"}),
    ):
        assert flow_matches_custom_blacklist(flow) is True
