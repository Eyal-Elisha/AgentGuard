from __future__ import annotations

from pathlib import Path

from backend.custom_blacklist import (
    custom_blacklist_entry_matches,
    custom_blacklist_file_path,
    custom_blacklist_matches,
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


def test_custom_blacklist_file_path_uses_default_file():
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


def test_custom_blacklist_matches_subdomain():
    assert custom_blacklist_matches(
        "www.youtube.com",
        "https://www.youtube.com/watch?v=123",
        frozenset({"youtube.com"}),
    ) is True
