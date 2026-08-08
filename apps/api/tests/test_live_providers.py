from __future__ import annotations

import os

import pytest
from personal_ai_os_core import Message, MessageRole
from personal_ai_os_providers import AnthropicAdapter, OpenAIAdapter


def _model(env_name: str, fallback: str) -> str:
    return next((item.strip() for item in os.getenv(env_name, fallback).split(",") if item.strip()), fallback)


def _message() -> list[Message]:
    return [Message(id="live-smoke", conversation_id="live-smoke", role=MessageRole.USER, content="Reply with only the word OK.")]


@pytest.mark.live_provider
@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("PERSONAL_AI_OS_OPENAI_API_KEY"), reason="OpenAI server-side API key is not configured")
async def test_openai_live_smoke() -> None:
    model = _model("PERSONAL_AI_OS_OPENAI_MODELS", "gpt-4.1-mini")
    adapter = OpenAIAdapter(os.getenv("PERSONAL_AI_OS_OPENAI_API_KEY"), (model,), 45, 1)
    output = "".join([item async for item in adapter.stream(_message(), model)])
    assert output.strip()


@pytest.mark.live_provider
@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("PERSONAL_AI_OS_ANTHROPIC_API_KEY"), reason="Anthropic server-side API key is not configured")
async def test_anthropic_live_smoke() -> None:
    model = _model("PERSONAL_AI_OS_ANTHROPIC_MODELS", "claude-haiku-4-5")
    adapter = AnthropicAdapter(os.getenv("PERSONAL_AI_OS_ANTHROPIC_API_KEY"), (model,), 45, 1)
    output = "".join([item async for item in adapter.stream(_message(), model)])
    assert output.strip()
