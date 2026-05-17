from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from backend.proxy.warn_bypass import BYPASS_QUERY_PARAM
from backend.proxy.warn_interstitial import append_bypass_param, build_warn_html


def test_append_bypass_param_no_existing_query():
    out = append_bypass_param("https://example.com/login", "tok")
    assert parse_qs(urlsplit(out).query) == {BYPASS_QUERY_PARAM: ["tok"]}


def test_append_bypass_param_preserves_existing_query():
    out = append_bypass_param("https://example.com/login?next=/x&keep=1", "tok")
    parsed = parse_qs(urlsplit(out).query)
    assert parsed["next"] == ["/x"]
    assert parsed["keep"] == ["1"]
    assert parsed[BYPASS_QUERY_PARAM] == ["tok"]


def test_append_bypass_param_replaces_stale_token():
    out = append_bypass_param(
        f"https://example.com/?{BYPASS_QUERY_PARAM}=old&x=1", "new"
    )
    parsed = parse_qs(urlsplit(out).query)
    assert parsed[BYPASS_QUERY_PARAM] == ["new"]
    assert parsed["x"] == ["1"]


def test_build_warn_html_includes_url_score_rules_and_continue_link():
    body = build_warn_html(
        original_url="https://evil.example.com/account",
        bypass_token="tok-123",
        risk_score=0.42,
        evaluation={
            "risk_score": 0.42,
            "rule_results": [
                {
                    "rule_id": "sensitive_fields",
                    "rule_type": "deterministic",
                    "score": 1.0,
                    "explanation": "Page contains password input",
                    "triggered": True,
                },
                {
                    "rule_id": "non_triggered",
                    "rule_type": "deterministic",
                    "score": 0.0,
                    "explanation": "Should not appear",
                    "triggered": False,
                },
            ],
        },
        safe_back_url="http://127.0.0.1:5000/",
    )
    text = body.decode("utf-8")
    assert "evil.example.com/account" in text
    assert "sensitive_fields" in text
    assert "Should not appear" not in text  # non-triggered rules are filtered
    assert "0.42" in text
    assert "tok-123" in text
    assert "Continue anyway" in text
    assert "Go back" in text
    # The "Continue anyway" link carries the bypass token as a URL param.
    assert f"{BYPASS_QUERY_PARAM}=tok-123" in text
    # The "Go back" JS target is the configured dashboard URL.
    assert "127.0.0.1:5000" in text


def test_build_warn_html_escapes_user_supplied_strings():
    body = build_warn_html(
        original_url="https://example.com/?<script>alert(1)</script>",
        bypass_token="tok",
        risk_score=0.3,
        evaluation={
            "rule_results": [
                {
                    "rule_id": "<bad>",
                    "rule_type": "deterministic",
                    "score": 1.0,
                    "explanation": "<img src=x onerror=alert(1)>",
                    "triggered": True,
                },
            ],
        },
        safe_back_url="http://127.0.0.1:5000/",
    )
    text = body.decode("utf-8")
    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in text
    assert "<img src=x onerror=alert(1)>" not in text


def test_build_warn_html_handles_missing_evaluation():
    body = build_warn_html(
        original_url="https://example.com/",
        bypass_token="tok",
        risk_score=None,
        evaluation=None,
        safe_back_url="http://127.0.0.1:5000/",
    )
    text = body.decode("utf-8")
    assert "AgentGuard" in text
    assert "—" in text  # score placeholder when missing
