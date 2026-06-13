"""Prompt payload mutation helpers."""

from __future__ import annotations

from typing import Any

from .constants import FALLBACK_INSTRUCTION

_USER_ROLES = frozenset({"user", "human"})
_INSTRUCTION_KEYS = frozenset({
    "instructions",
    "system",
    "system_message",
    "system_prompt",
    "developer",
    "developer_message",
    "developer_prompt",
})
_TEXT_KEYS = frozenset({
    "prompt",
    "input",
    "query",
    "question",
    "text",
    "message",
    "user_message",
    "input_text",
})
_TEXT_TYPE_KEYS = frozenset({"text", "input_text", "message_text"})


def _append_instruction(text: str) -> str:
    if FALLBACK_INSTRUCTION in text:
        return text
    separator = "\n\n" if text.strip() else ""
    return f"{text}{separator}{FALLBACK_INSTRUCTION}"


def _augment_message_content(content: Any) -> Any:
    if isinstance(content, str):
        return _append_instruction(content)
    if not isinstance(content, list):
        return content
    updated = []
    for item in content:
        if (
            isinstance(item, dict)
            and str(item.get("type", "")).lower() in _TEXT_TYPE_KEYS
            and isinstance(item.get("text"), str)
        ):
            copied = dict(item)
            copied["text"] = _append_instruction(copied["text"])
            updated.append(copied)
        else:
            updated.append(item)
    return updated


def _is_user_message_node(node: dict[str, Any]) -> bool:
    role = node.get("role")
    return isinstance(role, str) and role.strip().lower() in _USER_ROLES


def _augment_text_fields(node: dict[str, Any], only_known_keys: bool) -> bool:
    changed = False
    for key, value in list(node.items()):
        if not isinstance(value, str):
            continue
        if only_known_keys and key not in _TEXT_KEYS and key not in _INSTRUCTION_KEYS:
            continue
        updated = _append_instruction(value)
        if updated != value:
            node[key] = updated
            changed = True
    return changed


def augment_payload(payload: Any, in_user_scope: bool = False) -> bool:
    changed = False
    if isinstance(payload, dict):
        user_scope = in_user_scope or _is_user_message_node(payload)
        if user_scope:
            before = payload.get("content")
            after = _augment_message_content(before)
            if after != before:
                payload["content"] = after
                changed = True
        changed = _augment_text_fields(payload, only_known_keys=True) or changed
        for value in list(payload.values()):
            if isinstance(value, (dict, list)):
                changed = augment_payload(value, in_user_scope=user_scope) or changed
    elif isinstance(payload, list):
        for item in payload:
            changed = augment_payload(item, in_user_scope=in_user_scope) or changed
    return changed

