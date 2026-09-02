from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from personal_ai_os_providers import ProviderError

from personal_ai_os.chat import stream_chat
from personal_ai_os.schemas import ChatRequest


async def _events(runtime, request: ChatRequest) -> str:
    return "".join([item async for item in stream_chat(runtime, request)])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("code", "status_code", "retryable", "should_fallback"),
    [
        ("invalid_credentials", 401, False, False),
        ("forbidden", 403, False, False),
        ("timeout", 408, True, True),
        ("rate_limited", 429, True, True),
        ("upstream_5xx", 503, True, True),
        ("context_overflow", 400, True, True),
        ("malformed_stream", None, True, True),
        ("tool_unsupported", 400, False, False),
    ],
)
async def test_deterministic_provider_faults_follow_routing_policy(
    runtime, monkeypatch: pytest.MonkeyPatch, code: str, status_code: int | None, retryable: bool, should_fallback: bool
) -> None:
    runtime.database.migrate()
    runtime.database.set_setting("routing_policy", "FALLBACK_ALLOWED")
    runtime.database.set_setting("fallback_provider", "anthropic")
    runtime.database.set_setting("fallback_model", "anthropic-test")

    async def failing_stream(*_args, **_kwargs) -> AsyncIterator[str]:
        if False:
            yield "unused"
        raise ProviderError(code, code=code, status_code=status_code, retryable=retryable)

    monkeypatch.setattr(runtime.providers.get("openai"), "stream", failing_stream)
    events = await _events(
        runtime,
        ChatRequest(provider="openai", model="openai-test", project_id="general", content=f"Fault: {code}"),
    )
    assert ("event: routing" in events) is should_fallback
    if should_fallback:
        assert '"to_provider": "anthropic"' in events
        with runtime.database.connect() as connection:
            usage = connection.execute("SELECT provider, token_precision, cost_precision FROM usage_ledger").fetchone()
        assert dict(usage) == {"provider": "anthropic", "token_precision": "ESTIMATED", "cost_precision": "UNKNOWN"}
    else:
        assert "event: error" in events
        assert f'"code": "{code}"' in events


@pytest.mark.asyncio
async def test_partial_stream_and_tool_request_never_silently_splice_provider_outputs(runtime, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime.database.migrate()
    runtime.database.set_setting("routing_policy", "FALLBACK_ALLOWED")
    runtime.database.set_setting("fallback_provider", "anthropic")
    runtime.database.set_setting("fallback_model", "anthropic-test")

    async def partial_stream(*_args, **_kwargs) -> AsyncIterator[str]:
        yield "preferred partial"
        raise ProviderError("stream disconnected", code="stream_disconnect", retryable=True)

    monkeypatch.setattr(runtime.providers.get("openai"), "stream", partial_stream)
    partial = await _events(
        runtime,
        ChatRequest(provider="openai", model="openai-test", project_id="general", content="Do not splice output."),
    )
    assert "preferred partial" in partial
    assert "event: routing" not in partial
    assert "from anthropic/anthropic-test" not in partial

    tool_request = await _events(
        runtime,
        ChatRequest(
            provider="openai",
            model="openai-test",
            project_id="general",
            content="Use only the offered local tool.",
            tool={"name": "system.echo", "arguments": {"message": "safe"}},
        ),
    )
    assert "event: tool_start" in tool_request
    assert "event: routing" not in tool_request
    assert "event: error" in tool_request


@pytest.mark.asyncio
async def test_ask_before_fallback_requires_explicit_request_confirmation(runtime, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime.database.migrate()
    runtime.database.set_setting("routing_policy", "ASK_BEFORE_FALLBACK")
    runtime.database.set_setting("fallback_provider", "anthropic")
    runtime.database.set_setting("fallback_model", "anthropic-test")

    async def timeout_stream(*_args, **_kwargs) -> AsyncIterator[str]:
        if False:
            yield "unused"
        raise ProviderError("timed out", code="timeout", status_code=408, retryable=True)

    monkeypatch.setattr(runtime.providers.get("openai"), "stream", timeout_stream)
    without_confirmation = await _events(
        runtime,
        ChatRequest(provider="openai", model="openai-test", project_id="general", content="Ask first."),
    )
    assert "event: routing" not in without_confirmation
    with_confirmation = await _events(
        runtime,
        ChatRequest(
            provider="openai", model="openai-test", project_id="general", content="Fallback is approved.", allow_fallback=True
        ),
    )
    assert "event: routing" in with_confirmation


@pytest.mark.asyncio
async def test_cancellation_is_retry_safe_and_does_not_fallback(runtime) -> None:
    runtime.database.migrate()

    async def disconnected() -> bool:
        return True

    events = "".join(
        [
            item
            async for item in stream_chat(
                runtime,
                ChatRequest(provider="openai", model="openai-test", project_id="general", content="Cancel safely."),
                disconnected,
            )
        ]
    )
    assert "event: routing" not in events
    with runtime.database.connect() as connection:
        row = connection.execute("SELECT status, retry_status, side_effect_status FROM execution_runs").fetchone()
    assert dict(row) == {"status": "cancelled", "retry_status": "retry_safe", "side_effect_status": "not_started"}
