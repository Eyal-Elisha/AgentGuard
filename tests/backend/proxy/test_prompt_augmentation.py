from __future__ import annotations

import json
from types import SimpleNamespace

from backend.proxy.prompting import FALLBACK_INSTRUCTION, augment_request_body


def _make_request(body: dict, content_type: str = "application/json"):
    raw = json.dumps(body)
    request = SimpleNamespace(
        headers={"content-type": content_type},
        content=raw.encode("utf-8"),
        get_text=lambda: raw,
    )
    return request


def test_augment_messages_user_content():
    request = _make_request(
        {
            "messages": [
                {"role": "system", "content": "rules"},
                {"role": "user", "content": "Find flights to Paris"},
            ]
        }
    )

    augment_request_body(request)
    payload = json.loads(request.content.decode("utf-8"))
    assert FALLBACK_INSTRUCTION in payload["messages"][1]["content"]
    assert FALLBACK_INSTRUCTION not in payload["messages"][0]["content"]


def test_augment_prompt_field():
    request = _make_request({"prompt": "summarize this article"})

    augment_request_body(request)
    payload = json.loads(request.content.decode("utf-8"))
    assert FALLBACK_INSTRUCTION in payload["prompt"]


def test_augment_is_idempotent():
    initial = f"help me research this\n\n{FALLBACK_INSTRUCTION}"
    request = _make_request({"messages": [{"role": "user", "content": initial}]})

    augment_request_body(request)
    payload = json.loads(request.content.decode("utf-8"))
    assert payload["messages"][0]["content"].count(FALLBACK_INSTRUCTION) == 1


def test_augment_responses_style_input_text():
    request = _make_request(
        {
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": "book me a safe hotel in berlin"}],
                }
            ]
        }
    )

    augment_request_body(request)
    payload = json.loads(request.content.decode("utf-8"))
    text = payload["input"][0]["content"][0]["text"]
    assert FALLBACK_INSTRUCTION in text


def test_augment_nested_user_message_key():
    request = _make_request(
        {
            "conversation": {
                "turn": {
                    "role": "user",
                    "user_message": "find me a coding challenge website",
                }
            }
        }
    )

    augment_request_body(request)
    payload = json.loads(request.content.decode("utf-8"))
    text = payload["conversation"]["turn"]["user_message"]
    assert FALLBACK_INSTRUCTION in text
