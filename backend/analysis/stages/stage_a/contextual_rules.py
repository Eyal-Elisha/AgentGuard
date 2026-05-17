"""Contextual rule implementations for Stage A.

Each rule consumes a `SessionContext` (prior events plus the current request's
timestamp/host) and a per-rule config dict, and returns
`(score, explanation)`. When the rule's preconditions are absent
(e.g. there is no prior session at all, no prior warning to anchor against,
no candidate redirect chain) the rule returns `score=None` so that the
aggregator treats it as skipped — exactly the way deterministic rules use
`None` to mean "did not run / not applicable". When the preconditions exist
but no signal is present the rule returns `0.0` per the spec
`min(N / Nmax, 1)` with `N = 0`.

Both "sensitive event" and "warning" resolve to
`guard_action in {Warn, Block}` — i.e. anything AgentGuard previously flagged.
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

    Counts flagged events in the closed window `[t0 - T, t0]`. Skipped (None)
    when there is no current timestamp or no prior session data.
    """
    t0 = session.current_event_timestamp
    if t0 is None or not session.prior_events:
        return None, "Skipped — no session timestamp or prior events"

    n_max = int(config.get("Nmax", 5))
    t_ms = int(config.get("T_ms", 60_000))
    window_start = t0 - timedelta(milliseconds=t_ms)

    count = sum(
        1
        for event in session.prior_events
        if window_start <= event.timestamp <= t0 and _is_flagged(event)
    )
    score = _saturate(count, n_max)
    if count == 0:
        return 0.0, f"No flagged events in the last {t_ms} ms"
    return score, f"{count} flagged event(s) in the last {t_ms} ms (Nmax={n_max})"


def rule_repeated_sensitive_action_after_warning(
    session: SessionContext,
    config: Dict[str, Any],
) -> Tuple[Optional[float], str]:
    """Rule — Repeated Sensitive Action After Warning.

    Skipped (None) when there is no prior warning to anchor against.
    """
    n_max = int(config.get("Nmax", 5))
    t_warn = _first_flagged_timestamp(session)
    if t_warn is None:
        return None, "Skipped — no prior warning in this session"

    count = sum(
        1
        for event in session.prior_events
        if event.timestamp > t_warn and _is_flagged(event)
    )
    score = _saturate(count, n_max)
    if count == 0:
        return 0.0, "No repeated flagged events after the first session warning"
    return score, f"{count} flagged event(s) after the first session warning (Nmax={n_max})"


def rule_redirect_to_sensitive_action(
    session: SessionContext,
    config: Dict[str, Any],
) -> Tuple[Optional[float], str]:
    """Rule — Redirect to Sensitive Action.

    Walks backwards from the current event, treating each prior same-session
    event as a redirect link iff the gap to the next link is
    `<= redirect_window_ms`. Cross-domain links contribute `2`, same-domain `1`.
    Skipped (None) when no chain exists within the window.
    """
    t0 = session.current_event_timestamp
    if t0 is None or not session.prior_events:
        return None, "Skipped — no prior events to form a redirect chain"

    n_max = int(config.get("Nmax", 5))
    window_ms = int(config.get("redirect_window_ms", 2_000))
    window = timedelta(milliseconds=window_ms)

    n_redirect = 0
    chain_links = 0
    next_timestamp = t0
    next_host = session.current_event_host or ""

    for event in reversed(session.prior_events):
        if event.timestamp > next_timestamp:
            continue
        if next_timestamp - event.timestamp > window:
            break
        cross = 1 if (event.host and next_host and event.host != next_host) else 0
        n_redirect += 1 + cross
        chain_links += 1
        next_timestamp = event.timestamp
        next_host = event.host

    if chain_links == 0:
        return None, "Skipped — no redirect chain detected within the configured window"

    score = _saturate(n_redirect, n_max)
    return score, (
        f"Redirect chain of {chain_links} hop(s), weighted count={n_redirect} "
        f"(window={window_ms} ms, Nmax={n_max})"
    )


def rule_previously_warned_domain_in_session(
    session: SessionContext,
    config: Dict[str, Any],
) -> Tuple[Optional[float], str]:
    """Rule — Previously Warned Domain in Session.

    Skipped (None) when the session has no flagged events to define W.
    """
    n_max = int(config.get("Nmax", 5))
    if not session.prior_events:
        return None, "Skipped — no prior events in this session"

    warned: set = {
        event.host
        for event in session.prior_events
        if _is_flagged(event) and event.host
    }
    if not warned:
        return None, "Skipped — no previously warned domains in this session"

    count = sum(1 for event in session.prior_events if event.host in warned)
    if session.current_event_host and session.current_event_host in warned:
        count += 1

    score = _saturate(count, n_max)
    if count == 0:
        return 0.0, "No revisits to previously warned domains"
    return score, (
        f"{count} visit(s) to previously warned domain(s) {sorted(warned)[:5]} "
        f"(Nmax={n_max})"
    )


CONTEXTUAL_RULE_FN: Dict[str, Callable[[SessionContext, Dict[str, Any]], Tuple[Optional[float], str]]] = {
    "sensitive_action_frequency_spike":        rule_sensitive_action_frequency_spike,
    "repeated_sensitive_action_after_warning": rule_repeated_sensitive_action_after_warning,
    "redirect_to_sensitive_action":            rule_redirect_to_sensitive_action,
    "previously_warned_domain_in_session":     rule_previously_warned_domain_in_session,
}
