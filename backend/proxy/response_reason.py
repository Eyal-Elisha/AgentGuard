"""Build the final browser-visible reason for blocked requests."""

from __future__ import annotations


def browser_block_reason(
    *,
    current_reason: str,
    event_reason: str,
    has_event_evidence: bool,
) -> str:
    if not has_event_evidence:
        return current_reason or event_reason
    if not current_reason:
        return event_reason
    if current_reason.startswith("AgentGuard blocked"):
        return current_reason
    if current_reason.startswith("Blocked reason:"):
        return current_reason.removeprefix("Blocked reason:").strip()
    if event_reason in current_reason:
        return current_reason
    return f"{event_reason}\n\nSession context:\n{current_reason}"
