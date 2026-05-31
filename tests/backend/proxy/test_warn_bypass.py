from __future__ import annotations

import pytest

from backend.proxy.warn_bypass import WarnBypassStore


def test_mint_then_consume_returns_url():
    store = WarnBypassStore(ttl_seconds=60.0)
    token = store.mint("https://example.com/login", now=1_000.0)
    assert store.consume(token, now=1_000.5) == "https://example.com/login"


def test_consume_is_single_use():
    store = WarnBypassStore(ttl_seconds=60.0)
    token = store.mint("https://example.com/", now=0.0)
    first = store.consume(token, now=1.0)
    second = store.consume(token, now=2.0)
    assert first == "https://example.com/"
    assert second is None


def test_unknown_token_returns_none():
    store = WarnBypassStore(ttl_seconds=60.0)
    assert store.consume("not-a-real-token", now=0.0) is None


def test_empty_token_returns_none():
    store = WarnBypassStore(ttl_seconds=60.0)
    assert store.consume("", now=0.0) is None


def test_expired_token_returns_none_and_is_swept():
    store = WarnBypassStore(ttl_seconds=10.0)
    token = store.mint("https://example.com/", now=100.0)
    # Past TTL: consume must reject and the entry must not linger.
    assert store.consume(token, now=200.0) is None
    # Even at the original time the token is gone (was swept on consume).
    assert store.consume(token, now=100.0) is None


def test_distinct_tokens_for_distinct_mints():
    store = WarnBypassStore(ttl_seconds=60.0)
    a = store.mint("https://example.com/a", now=0.0)
    b = store.mint("https://example.com/b", now=0.0)
    assert a != b
    assert store.consume(a, now=0.0) == "https://example.com/a"
    assert store.consume(b, now=0.0) == "https://example.com/b"
