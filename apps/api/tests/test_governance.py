import pytest
from fastapi.testclient import TestClient
from personal_ai_os_providers import ProviderTimeout
from personal_ai_os.schemas import ChatRequest
from personal_ai_os.chat import stream_chat


def test_send_scope_usage_budget_and_execution_receipts(client: TestClient) -> None:
    preview = client.post(
        "/api/send-scope/preview",
        json={
            "provider": "openai",
            "model": "openai-test",
            "project_id": "general",
            "content": "Explain the current project state.",
        },
    )
    assert preview.status_code == 200
    assert preview.json()["secrets_included"] is False
    assert preview.json()["context_precision"] == "ESTIMATED"

    response = client.post(
        "/api/chat/stream",
        json={
            "provider": "openai",
            "model": "openai-test",
            "project_id": "general",
            "content": "Record a governed request.",
        },
    )
    assert response.status_code == 200
    assert "event: context" in response.text
    done = [block for block in response.text.split("\n\n") if "event: done" in block][-1]
    assert "execution_id" in done
    assert client.get("/api/usage?project_id=general").json()["items"][0]["token_precision"] == "ESTIMATED"

    saved = client.put(
        "/api/budgets",
        json={
            "scope_type": "project",
            "scope_id": "general",
            "period": "daily",
            "limit_tokens": 1,
            "warn_percent": 80,
            "hard_limit": True,
        },
    )
    assert saved.status_code == 200
    blocked = client.post(
        "/api/chat/stream",
        json={
            "provider": "openai",
            "model": "openai-test",
            "project_id": "general",
            "content": "This request should be stopped by the budget.",
        },
    )
    assert "budget_hard_limit" in blocked.text


def test_memory_conflict_is_never_activated_automatically(client: TestClient) -> None:
    active = client.post(
        "/api/memory",
        json={
            "type": "preference",
            "text": "timezone=UTC",
            "source": "test",
            "project_id": "general",
        },
    )
    assert active.status_code == 201
    conflict = client.post(
        "/api/memory",
        json={
            "type": "preference",
            "text": "timezone=Asia/Shanghai",
            "source": "test",
            "project_id": "general",
        },
    )
    assert conflict.status_code == 201
    assert conflict.json()["status"] == "conflict_review_required"


@pytest.mark.asyncio
async def test_retryable_preoutput_failure_can_use_confirmed_fallback(runtime, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime.database.migrate()
    runtime.database.set_setting("routing_policy", "FALLBACK_ALLOWED")
    runtime.database.set_setting("fallback_provider", "anthropic")
    runtime.database.set_setting("fallback_model", "anthropic-test")

    async def unavailable_stream(*_args, **_kwargs):
        if False:
            yield "never"
        raise ProviderTimeout("OpenAI timed out", code="timeout", retryable=True)

    monkeypatch.setattr(runtime.providers.get("openai"), "stream", unavailable_stream)
    output = "".join(
        [
            item
            async for item in stream_chat(
                runtime,
                ChatRequest(
                    provider="openai",
                    model="openai-test",
                    project_id="general",
                    content="Use the fallback only after the preferred provider fails.",
                ),
            )
        ]
    )
    assert "event: routing" in output
    assert '"to_provider": "anthropic"' in output
    assert "from anthropic/anthropic-test" in output
