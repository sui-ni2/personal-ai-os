from __future__ import annotations

import json

import httpx
import pytest
from personal_ai_os_core import Message, MessageRole
from personal_ai_os_providers import (
    AnthropicAdapter,
    OpenAIAdapter,
    ProviderRateLimited,
    ProviderStreamInterrupted,
    ProviderTool,
    ProviderToolCall,
)


def _messages() -> list[Message]:
    return [Message(id="message-1", conversation_id="conversation-1", role=MessageRole.USER, content="Echo hello.")]


def _tool() -> ProviderTool:
    return ProviderTool(
        name="system.echo",
        description="Echo a message.",
        input_schema={"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
    )


@pytest.mark.asyncio
async def test_openai_retries_rate_limit_and_parses_stream() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, request=request)
        body = 'data: {"choices":[{"delta":{"content":"recovered"}}]}\n\ndata: [DONE]\n\n'
        return httpx.Response(200, text=body, request=request)

    adapter = OpenAIAdapter(
        "test-key", ("test-model",), max_retries=1, retry_base_seconds=0,
        transport=httpx.MockTransport(handler), endpoint="https://test.openai.local/messages",
    )
    assert [item async for item in adapter.stream(_messages(), "test-model")] == ["recovered"]
    assert attempts == 2


@pytest.mark.asyncio
async def test_openai_normalizes_rate_limit_after_retry_budget() -> None:
    adapter = OpenAIAdapter(
        "test-key", ("test-model",), max_retries=0,
        transport=httpx.MockTransport(lambda request: httpx.Response(429, request=request)),
        endpoint="https://test.openai.local/messages",
    )
    with pytest.raises(ProviderRateLimited) as error:
        _ = [item async for item in adapter.stream(_messages(), "test-model")]
    assert error.value.code == "rate_limited"
    assert error.value.retryable is True


@pytest.mark.asyncio
async def test_openai_detects_partial_stream_interruption() -> None:
    body = 'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
    adapter = OpenAIAdapter(
        "test-key", ("test-model",),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text=body, request=request)),
        endpoint="https://test.openai.local/messages",
    )
    with pytest.raises(ProviderStreamInterrupted):
        _ = [item async for item in adapter.stream(_messages(), "test-model")]


@pytest.mark.asyncio
async def test_provider_tool_call_parsing_for_openai_and_anthropic() -> None:
    openai_payload = {
        "choices": [{"message": {"tool_calls": [{"id": "call-openai", "function": {"name": "system_echo", "arguments": json.dumps({"message": "hello"})}}]}}]
    }
    openai = OpenAIAdapter(
        "test-key", ("test-model",),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=openai_payload, request=request)),
        endpoint="https://test.openai.local/messages",
    )
    openai_call = await openai.request_tool(_messages(), "test-model", _tool())
    assert openai_call.name == "system.echo"
    assert openai_call.arguments == {"message": "hello"}

    anthropic_payload = {"content": [{"type": "tool_use", "id": "call-anthropic", "name": "system_echo", "input": {"message": "hello"}}]}
    anthropic = AnthropicAdapter(
        "test-key", ("test-model",),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=anthropic_payload, request=request)),
        endpoint="https://test.anthropic.local/messages",
    )
    anthropic_call = await anthropic.request_tool(_messages(), "test-model", _tool())
    assert anthropic_call.name == "system.echo"
    assert anthropic_call.arguments == {"message": "hello"}


@pytest.mark.asyncio
async def test_provider_followup_uses_native_tool_result_protocol() -> None:
    captured: list[dict[str, object]] = []

    def openai_handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        body = 'data: {"choices":[{"delta":{"content":"done"}}]}\n\ndata: [DONE]\n\n'
        return httpx.Response(200, text=body, request=request)

    call = ProviderToolCall(
        id="call-1", name="system.echo", arguments={"message": "hello"}
    )
    openai = OpenAIAdapter(
        "test-key", ("test-model",), transport=httpx.MockTransport(openai_handler),
        endpoint="https://test.openai.local/messages",
    )
    assert [
        item
        async for item in openai.stream_after_tool(
            _messages(), "test-model", call, {"content": [{"text": "hello"}]}
        )
    ] == ["done"]
    openai_messages = captured.pop()["messages"]
    assert openai_messages[-2]["tool_calls"][0]["function"]["name"] == "system_echo"
    assert openai_messages[-1]["role"] == "tool"

    def anthropic_handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        body = 'data: {"type":"content_block_delta","delta":{"text":"done"}}\n\ndata: {"type":"message_stop"}\n\n'
        return httpx.Response(200, text=body, request=request)

    anthropic = AnthropicAdapter(
        "test-key", ("test-model",), transport=httpx.MockTransport(anthropic_handler),
        endpoint="https://test.anthropic.local/messages",
    )
    assert [
        item
        async for item in anthropic.stream_after_tool(
            _messages(), "test-model", call, {"content": [{"text": "hello"}]}
        )
    ] == ["done"]
    anthropic_messages = captured.pop()["messages"]
    assert anthropic_messages[-2]["content"][0]["name"] == "system_echo"
    assert anthropic_messages[-1]["content"][0]["type"] == "tool_result"
