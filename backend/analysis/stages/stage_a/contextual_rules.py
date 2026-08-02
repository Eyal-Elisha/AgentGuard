"""Contextual rule implementations for Stage A.

Each rule reads recent session activity (`SessionContext`) and returns a score
plus a short explanation for the user. If the rule does not apply (e.g. no
prior history yet), it returns `score=None` so aggregation ignores it. If it
applies but nothing suspicious was found, the score is `0.0`.

Scores rise with how strong the pattern is and are capped at 1.0 using each
rule's `max_events` setting in `CONTEXTUAL_RULE_CONFIG`.

A prior "warning" for these rules means AgentGuard already marked an earlier
request as Warn or Block for that session (`guard_action` in `{Warn, Block}`).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Callable, Dict, Optional, Tuple

from backend.analysis.rules import PriorEvent, SessionContext


_FLAGGED_ACTIONS = frozenset({"Warn", "Block"})


def _is_flagged(event: PriorEvent) -> bool:
    return event.guard_action in _FLAGGED_ACTIONS


def _saturate(numerator: float, n_max: int) -> float:
    if n_max <= 0:
        return 0.0
    return min(numerator / float(n_max), 1.0)


def _first_flagged_timestamp(session: SessionContext):
    for event in session.prior_events:
        if _is_flagged(event):
            return event.timestamp
    return None


def rule_sensitive_action_frequency_spike(
    session: SessionContext,
    config: Dict[str, Any],
) -> Tuple[Optional[float], str]:
    """Rule — Sensitive Action Frequency Spike.

    Detects bursts of risky pages in a short window — characteristic of
    automated activity or a phishing flow, not normal human browsing.

    Counts flagged events in the closed window `[t0 - T, t0]`. Skipped
    (None) when there is no current timestamp or no prior session data.
    """
    t0 = session.current_event_timestamp
    if t0 is None or not session.prior_events:
        return None, "Skipped - no browsing history yet in this session"

    n_max = int(config.get("max_events", 5))
    t_ms = int(config.get("window_ms", 60_000))
    window_seconds = max(1, t_ms // 1000)
    window_start = t0 - timedelta(milliseconds=t_ms)

    count = sum(
        1
        for event in session.prior_events
        if window_start <= event.timestamp <= t0 and _is_flagged(event)
    )
    score = _saturate(count, n_max)
    if count == 0:
        return 0.0, f"No suspicious pages visited in the last {window_seconds} seconds."
    pages_word = "page" if count == 1 else "pages"
    return score, (
        f"Visited {count} suspicious {pages_word} in the last {window_seconds} seconds - "
        f"a burst this fast is unusual for normal browsing and often indicates "
        f"automated activity or a phishing flow."
    )


def rule_repeated_sensitive_action_after_warning(
    session: SessionContext,
    config: Dict[str, Any],
) -> Tuple[Optional[float], str]:
    """Rule — Repeated Sensitive Action After Warning.

    Detects sessions that keep hitting risky pages after AgentGuard already
    warned them once. Strong signal that the user (or agent) is ignoring
    warnings, which is itself suspicious.

    Skipped (None) when there is no prior warning to anchor against.
    """
    n_max = int(config.get("max_events", 5))
    t_warn = _first_flagged_timestamp(session)
    if t_warn is None:
        return None, "Skipped - AgentGuard hasn't warned you yet in this session"

    count = sum(
        1
        for event in session.prior_events
        if event.timestamp > t_warn and _is_flagged(event)
    )
    score = _saturate(count, n_max)
    if count == 0:
        return 0.0, "You haven't hit any more suspicious pages since AgentGuard's first warning."
    pages_word = "page" if count == 1 else "pages"
    return score, (
        f"Visited {count} more suspicious {pages_word} after AgentGuard already warned "
        f"you earlier in this session - repeated warnings being ignored is itself a "
        f"red flag."
    )


def rule_redirect_to_sensitive_action(
    session: SessionContext,
    config: Dict[str, Any],
) -> Tuple[Optional[float], str]:
    """Rule — Redirect to Sensitive Action.

    Detects rapid redirect chains leading into the current page —
    especially across different domains. Phishing kits and malicious ad
    redirects use this pattern to hide the real destination behind a few
    fast hops.

    Walks backwards from the current event, treating each prior
    same-session event as a redirect link iff the gap to the next link is
    `<= redirect_window_ms`. Cross-domain hops count double. Skipped
    (None) when no chain exists within the window.
    """
    t0 = session.current_event_timestamp
    if t0 is None or not session.prior_events:
        return None, "Skipped - no browsing history to form a redirect chain"

    n_max = int(config.get("max_events", 5))
    window_ms = int(config.get("redirect_window_ms", 2_000))
    window = timedelta(milliseconds=window_ms)

    n_redirect = 0
    chain_links = 0
    cross_domain_hops = 0
    next_timestamp = t0
    next_host = session.current_event_host or ""

    for event in reversed(session.prior_events):
        if event.timestamp > next_timestamp:
            continue
        if next_timestamp - event.timestamp > window:
            break
        is_cross = bool(event.host and next_host and event.host != next_host)
        cross = 1 if is_cross else 0
        if is_cross:
            cross_domain_hops += 1
        n_redirect += 1 + cross
        chain_links += 1
        next_timestamp = event.timestamp
        next_host = event.host

    if chain_links == 0:
        return None, "Skipped - you didn't arrive here through a rapid redirect chain"

    score = _saturate(n_redirect, n_max)
    window_seconds = max(1, window_ms // 1000)
    hop_word = "hop" if chain_links == 1 else "hops"
    cross_note = (
        f", {cross_domain_hops} of them across different domains"
        if cross_domain_hops
        else ""
    )
    return score, (
        f"You arrived here through {chain_links} fast {hop_word}"
        f"{cross_note} (each within {window_seconds} second(s)) - "
        f"a pattern phishing kits commonly use to hide the real destination."
    )


def rule_previously_warned_domain_in_session(
    session: SessionContext,
    config: Dict[str, Any],
) -> Tuple[Optional[float], str]:
    """Rule — Previously Warned Domain in Session.

    Detects repeated traffic to domains AgentGuard already flagged in
    this session. Coming back to a domain we already warned about is a
    strong signal — especially relevant for autonomous agents that might
    not realize a host is dangerous.

    Skipped (None) when the session has no flagged events to define
    a "warned-domain set".
    """
    n_max = int(config.get("max_events", 5))
    if not session.prior_events:
        return None, "Skipped - no browsing history yet in this session"

    warned: set = {
        event.host
        for event in session.prior_events
        if _is_flagged(event) and event.host
    }
    if not warned:
        return None, "Skipped - AgentGuard hasn't flagged any domains yet in this session"

    count = sum(1 for event in session.prior_events if event.host in warned)
    if session.current_event_host and session.current_event_host in warned:
        count += 1

    score = _saturate(count, n_max)
    if count == 0:
        return 0.0, "You haven't revisited any domain AgentGuard previously flagged."
    sample = sorted(warned)[:3]
    sample_text = ", ".join(sample)
    if len(warned) > 3:
        sample_text += f", and {len(warned) - 3} more"
    visit_word = "visit" if count == 1 else "visits"
    return score, (
        f"{count} {visit_word} this session to domain(s) AgentGuard already "
        f"flagged ({sample_text}). Coming back to a flagged domain is a strong "
        f"signal that something is going wrong."
    )


CONTEXTUAL_RULE_FN: Dict[str, Callable[[SessionContext, Dict[str, Any]], Tuple[Optional[float], str]]] = {
    "sensitive_action_frequency_spike":        rule_sensitive_action_frequency_spike,
    "repeated_sensitive_action_after_warning": rule_repeated_sensitive_action_after_warning,
    "redirect_to_sensitive_action":            rule_redirect_to_sensitive_action,
    "previously_warned_domain_in_session":     rule_previously_warned_domain_in_session,
}
