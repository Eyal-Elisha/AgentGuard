"""Guidance helpers for browserOS soft-block continuation payloads."""

from __future__ import annotations

from urllib.parse import quote_plus


def format_actionable_reason(reason: str, alternatives: list[dict[str, str]]) -> str:
    lines: list[str] = [reason.strip()]
    lines.append("Immediate next step: choose one safe alternative and continue without asking.")
    shown = 0
    for item in alternatives:
        if item.get("type") == "navigate" and isinstance(item.get("url"), str):
            lines.append(f"- Navigate to {item['url']}")
            shown += 1
        elif item.get("type") == "search" and isinstance(item.get("query"), str):
            lines.append(f"- Search: {item['query']}")
            shown += 1
        if shown >= 3:
            break
    return "\n".join(lines)


def recovery_auto_target(alternatives: list[dict[str, str]], dashboard_url: str) -> str:
    for item in alternatives:
        if item.get("type") == "navigate" and isinstance(item.get("url"), str):
            return item["url"]
    for item in alternatives:
        if item.get("type") == "search" and isinstance(item.get("query"), str):
            return f"https://www.google.com/search?q={quote_plus(item['query'])}"
    return dashboard_url


def required_next_action_text() -> str:
    return "Pick one safe alternative now, navigate to it, and continue the user task automatically."

