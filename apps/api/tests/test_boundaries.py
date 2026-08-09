from __future__ import annotations

import json
from pathlib import Path

from personal_ai_os_core import (
    Artifact,
    Conversation,
    EventType,
    ExecutionEvent,
    MemoryRecord,
    Message,
    ProjectRegistry,
    RepositoryEvent,
)
from personal_ai_os_projects import GeneralProject, create_project_registry

from personal_ai_os.db import Database


def test_core_models_have_no_soccer_fields() -> None:
    for model in (Artifact, Conversation, MemoryRecord, Message, RepositoryEvent):
        fields = set(model.model_fields)
        assert not any("soccer" in field.lower() for field in fields)
        assert not any("fixture" in field.lower() for field in fields)


def test_general_project_runs_without_soccer_plugin() -> None:
    registry = create_project_registry(include_soccer=False)
    assert [item.id for item in registry.list()] == ["general"]
    assert registry.get("general").metadata.name == "General"


def test_dummy_project_does_not_change_core_schema() -> None:
    before = set(Conversation.model_fields)
    registry = ProjectRegistry([GeneralProject()])

    class DummyProject(GeneralProject):
        metadata = GeneralProject.metadata.model_copy(update={"id": "dummy", "name": "Dummy"})

    registry.register(DummyProject())
    assert registry.get("dummy").metadata.name == "Dummy"
    assert set(Conversation.model_fields) == before


def test_sqlite_records_survive_database_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "persistent.db"
    first = Database(database_path)
    first.migrate()
    created = first.create_memory(
        {
            "type": "rule",
            "text": "Persistence is required.",
            "source": "test",
            "confidence": 1,
            "status": "active",
            "project_id": "general",
        }
    )
    second = Database(database_path)
    second.migrate()
    assert second.list_memories()[0].id == created.id


def test_execution_event_recursively_redacts_and_bounds_audit_payload() -> None:
    event = ExecutionEvent(
        id="event-safe",
        type=EventType.TOOL_RESULT,
        status="succeeded",
        payload={
            "result": {
                "apiKey": "nested-api-secret",
                "headers": {"Authorization": "Bearer nested-bearer-secret"},
                "safe": "visible",
                "url": "https://example.test/callback?token=query-secret&mode=safe",
                "long": "x" * 5_000,
                "deep": {"one": {"two": {"three": {"four": {"five": "hidden"}}}}},
            },
            "stack_trace": "private stack",
            "reasoning": "private reasoning",
            "many": list(range(70)),
        },
    )

    rendered = json.dumps(event.public_payload())
    for secret in (
        "nested-api-secret",
        "nested-bearer-secret",
        "query-secret",
        "private stack",
        "private reasoning",
        "hidden",
    ):
        assert secret not in rendered
    assert event.payload["result"]["safe"] == "visible"
    assert event.payload["result"]["apiKey"] == "[redacted]"
    assert event.payload["stack_trace"] == "[redacted]"
    assert event.payload["reasoning"] == "[redacted]"
    assert event.payload["result"]["long"].endswith("[truncated]")
    assert event.payload["many"][-1] == "[truncated]"


def test_execution_event_storage_is_safe_and_legacy_rows_are_redacted_on_read(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "audit.db")
    database.migrate()
    event = ExecutionEvent(
        id="event-new",
        type=EventType.TOOL_RESULT,
        status="succeeded",
        conversation_id="conversation-audit",
        payload={"result": {"client_secret": "new-storage-secret", "value": "safe"}},
    )
    database.add_execution_event(event.model_dump(mode="json"))
    database.add_execution_event(
        {
            "id": "event-legacy",
            "conversation_id": "conversation-audit",
            "type": "tool_result",
            "status": "succeeded",
            "payload": {"result": {"access_token": "legacy-storage-secret"}},
            "created_at": "2026-08-09T00:00:00+00:00",
        }
    )

    with database.connect() as connection:
        stored = connection.execute(
            "SELECT payload_json FROM execution_events WHERE id = ?", ("event-new",)
        ).fetchone()["payload_json"]
    assert "new-storage-secret" not in stored
    assert json.loads(stored)["result"]["client_secret"] == "[redacted]"

    restored = {item.id: item for item in database.list_execution_events("conversation-audit")}
    assert restored["event-legacy"].payload["result"]["access_token"] == "[redacted]"
