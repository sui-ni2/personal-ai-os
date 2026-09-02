from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from personal_ai_os_providers import ProviderError

from personal_ai_os.chat import stream_chat
from personal_ai_os.schemas import ChatRequest


async def _run(runtime, content: str) -> str:
    return "".join(
        [
            item
            async for item in stream_chat(
                runtime,
                ChatRequest(
                    provider="openai",
                    model="openai-test",
                    project_id="general",
                    content=content,
                ),
            )
        ]
    )


def _latest_state(runtime) -> dict[str, str]:
    with runtime.database.connect() as connection:
        row = connection.execute(
            "SELECT status, retry_status, side_effect_status FROM execution_runs ORDER BY created_at DESC, id DESC LIMIT 1"
        ).fetchone()
    return dict(row)


@pytest.mark.asyncio
async def test_execution_statuses_remain_explicit_across_success_and_provider_failures(
    runtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime.database.migrate()

    completed = await _run(runtime, "Complete a deterministic request.")
    assert "event: done" in completed
    assert _latest_state(runtime) == {
        "status": "completed",
        "retry_status": "retry_safe",
        "side_effect_status": "not_started",
    }

    async def invalid_credentials(*_args, **_kwargs) -> AsyncIterator[str]:
        if False:
            yield "unused"
        raise ProviderError("Invalid credentials", code="invalid_credentials", status_code=401, retryable=False)

    monkeypatch.setattr(runtime.providers.get("openai"), "stream", invalid_credentials)
    failed = await _run(runtime, "Fail without a side effect.")
    assert '"code": "invalid_credentials"' in failed
    assert _latest_state(runtime) == {
        "status": "failed",
        "retry_status": "retry_safe",
        "side_effect_status": "not_started",
    }

    async def timeout(*_args, **_kwargs) -> AsyncIterator[str]:
        if False:
            yield "unused"
        raise ProviderError("Timed out", code="timeout", status_code=408, retryable=True)

    monkeypatch.setattr(runtime.providers.get("openai"), "stream", timeout)
    interrupted = await _run(runtime, "Interrupt before a side effect.")
    assert '"code": "timeout"' in interrupted
    assert _latest_state(runtime) == {
        "status": "interrupted",
        "retry_status": "retry_safe",
        "side_effect_status": "not_started",
    }
