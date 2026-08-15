from __future__ import annotations

import json

import httpx
import pytest
from personal_ai_os_core import Message, MessageRole
from personal_ai_os_providers import OllamaAdapter


@pytest.mark.asyncio
async def test_ollama_optional_output_cap_is_sent_without_changing_default_behavior() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        body = 'data: {"choices":[{"delta":{"content":"ok"}}]}\n\ndata: [DONE]\n\n'
        return httpx.Response(200, text=body, request=request)

    model = "smollm2:135m-instruct-q2_K"
    adapter = OllamaAdapter(
        True,
        (model,),
        max_output_tokens=16,
        endpoint="http://ollama.test/v1/chat/completions",
        transport=httpx.MockTransport(handler),
    )
    messages = [
        Message(
            id="message-1",
            conversation_id="conversation-1",
            role=MessageRole.USER,
            content="Reply briefly.",
        )
    ]

    assert [item async for item in adapter.stream(messages, model)] == ["ok"]
    assert captured["max_tokens"] == 16
