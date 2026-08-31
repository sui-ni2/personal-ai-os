from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from personal_ai_os_core import Message

from personal_ai_os.chat import stream_chat
from personal_ai_os.governance import GovernanceService
from personal_ai_os.project_state import ProjectStateService
from personal_ai_os.schemas import ChatRequest


@pytest.mark.asyncio
async def test_send_scope_receipt_matches_serialized_provider_payload_and_never_expands_scope(
    runtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime.database.migrate()
    global_memory = runtime.database.create_memory(
        {"type": "preference", "text": "global-approved-context", "source": "test", "confidence": 1.0}
    )
    other_memory = runtime.database.create_memory(
        {"type": "preference", "text": "other-project-memory", "source": "test", "confidence": 1.0, "project_id": "soccer"}
    )
    runtime.database.create_artifact(
        {"kind": "file", "locator": "other-project-file-marker", "title": "Other project file", "project_id": "soccer"}
    )
    runtime.database.set_setting("internal_settings_marker", "do-not-send")
    state = ProjectStateService(runtime.database, data_dir=runtime.settings.data_dir, tenant_id=runtime.settings.tenant_id)
    state.put_state(
        project_id="general", namespace="current_state", key="scope", value={"marker": "general-project-state"}, source="test"
    )
    state.put_state(
        project_id="soccer", namespace="current_state", key="scope", value={"marker": "other-project-state"}, source="test"
    )

    captured: list[Message] = []

    async def capture_stream(messages: list[Message], _model: str) -> AsyncIterator[str]:
        captured.extend(messages)
        yield "verified"

    monkeypatch.setattr(runtime.providers.get("openai"), "stream", capture_stream)
    events = "".join(
        [
            item
            async for item in stream_chat(
                runtime,
                ChatRequest(provider="openai", model="openai-test", project_id="general", content="Use only authorized context."),
            )
        ]
    )
    assert "event: context" in events
    serialized = "\n".join(message.content for message in captured)
    assert "global-approved-context" in serialized
    assert "general-project-state" in serialized
    assert "other-project-memory" not in serialized
    assert "other-project-file-marker" not in serialized
    assert "other-project-state" not in serialized
    assert "internal_settings_marker" not in serialized
    assert "do-not-send" not in serialized

    with runtime.database.connect() as connection:
        row = connection.execute(
            "SELECT reviewed_memory_ids_json, selected_files_json, context_categories_json FROM send_scope_receipts"
        ).fetchone()
    assert global_memory.id in row["reviewed_memory_ids_json"]
    assert other_memory.id not in row["reviewed_memory_ids_json"]
    assert row["selected_files_json"] == "[]"
    assert "reviewed_memory" in row["context_categories_json"]
    assert runtime.database.get_memory(global_memory.id).last_used_at is not None
    assert runtime.database.get_memory(other_memory.id).last_used_at is None
    assert GovernanceService(runtime.database).send_scope_preview(
        runtime,
        ChatRequest(provider="openai", model="openai-test", project_id="general", content="Preview remains scoped."),
    )["secrets_included"] is False


def test_send_scope_preview_rejects_conversation_project_mutation(client) -> None:
    conversation = client.post(
        "/api/conversations",
        json={"provider": "openai", "model": "openai-test", "project_id": "general", "title": "General only"},
    ).json()
    response = client.post(
        "/api/send-scope/preview",
        json={
            "provider": "openai",
            "model": "openai-test",
            "project_id": "soccer",
            "conversation_id": conversation["id"],
            "content": "Attempt cross-project preview.",
        },
    )
    assert response.status_code == 400
    assert "cannot change project context" in response.json()["detail"]
