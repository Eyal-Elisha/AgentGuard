from __future__ import annotations

from backend.proxy.block_interstitial import build_block_html


def test_build_block_html_renders_url_score_and_rules():
    body = build_block_html(
        original_url="https://malware.example.com/payload",
        reason="URL matches the custom local blacklist",
        evaluation={
            "risk_score": 1.0,
            "rule_results": [
                {
                    "rule_id": "custom_blacklist",
                    "rule_type": "deterministic",
                    "score": 1.0,
                    "explanation": "Host is on the local blacklist",
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
    assert "This page has been blocked" in text
    assert "Blocked" in text
    assert "malware.example.com/payload" in text
    assert "custom_blacklist" in text
    assert "Host is on the local blacklist" in text
    assert "Should not appear" not in text
    assert "1.00" in text
    assert "127.0.0.1:5000" in text
    assert "Safe alternatives" in text
    # No "Continue anyway" path on block.
    assert "Continue anyway" not in text


def test_build_block_html_falls_back_to_reason_when_no_rules():
    body = build_block_html(
        original_url="https://blocked.example.com/",
        reason="Hard-blocked by the deterministic password-exfil rule",
        evaluation=None,
        safe_back_url="http://127.0.0.1:5000/",
    )
    text = body.decode("utf-8")
    assert "Hard-blocked by the deterministic password-exfil rule" in text
    assert "—" in text  # score placeholder when missing


def test_build_block_html_escapes_user_supplied_strings():
    body = build_block_html(
        original_url="https://example.com/?<script>alert(1)</script>",
        reason="<img src=x onerror=alert(2)>",
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
    assert "<img src=x onerror=alert(2)>" not in text


def test_build_block_html_suggests_generic_alternative_guidance():
    body = build_block_html(
        original_url="https://example.com/",
        reason="URL matches the custom local blacklist",
        evaluation=None,
        safe_back_url="http://127.0.0.1:5000/",
    )
    text = body.decode("utf-8")
    assert "Search for the official example.com website and continue there." in text
    assert "Try canonical domain: https://www.example.com" in text


def test_build_block_html_suggests_https_upgrade_for_http_url():
    body = build_block_html(
        original_url="http://neverssl.com/",
        reason="Connection is unencrypted ('http://')",
        evaluation=None,
        safe_back_url="http://127.0.0.1:5000/",
    )
    text = body.decode("utf-8")
    assert "https://neverssl.com/" in text
