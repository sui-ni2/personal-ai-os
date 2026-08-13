from __future__ import annotations

import json
from pathlib import Path

import pytest

from personal_ai_os_core import (
    Artifact,
    Conversation,
    EventType,
    ExecutionEvent,
    MemoryRecord,
    Message,
    MessageRole,
    ProjectRegistry,
    RepositoryEvent,
    Capability,
    DeploymentMode,
    PlanId,
    build_product_profile,
)
from personal_ai_os_projects import GeneralProject, create_project_registry

from personal_ai_os.db import Database
from personal_ai_os.config import Settings
from personal_ai_os.runtime import create_runtime


def test_core_models_have_no_soccer_fields() -> None:
    for model in (Artifact, Conversation, MemoryRecord, Message, RepositoryEvent):
        fields = set(model.model_fields)
        assert not any("soccer" in field.lower() for field in fields)
        assert not any("fixture" in field.lower() for field in fields)
        assert not any("p5" in field.lower() for field in fields)
        assert not any("candidate" in field.lower() for field in fields)


def test_general_project_runs_without_soccer_plugin() -> None:
    registry = create_project_registry(include_soccer=False, include_p5=False)
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


def test_database_scopes_core_records_and_settings_by_tenant(tmp_path: Path) -> None:
    database_path = tmp_path / "tenant-boundary.db"
    alpha = Database(database_path, tenant_id="tenant-alpha", actor_id="owner-alpha")
    alpha.migrate()
    alpha.create_memory(
        {
            "type": "rule",
            "text": "Alpha only",
            "source": "test",
            "confidence": 1,
            "status": "active",
            "project_id": "general",
        }
    )
    alpha.set_setting("default_model", "alpha-model")
    conversation = alpha.create_conversation(
        provider="openai",
        model="openai-test",
        project_id="general",
        title="Alpha conversation",
    )
    alpha.add_message(conversation.id, MessageRole.USER, "Alpha message")
    alpha.create_artifact(
        {
            "kind": "note",
            "locator": "alpha-note",
            "title": "Alpha outcome",
            "project_id": "general",
        }
    )
    alpha.add_execution_event(
        {
            "id": "alpha-event",
            "conversation_id": conversation.id,
            "type": "done",
            "status": "succeeded",
            "payload": {},
            "created_at": "2026-08-13T00:00:00+00:00",
        }
    )

    beta = Database(database_path, tenant_id="tenant-beta", actor_id="owner-beta")
    beta.migrate()
    assert beta.list_memories() == []
    assert beta.get_setting("default_model") is None
    assert beta.get_conversation(conversation.id) is None
    assert beta.list_messages(conversation.id) == []
    assert beta.list_artifacts() == []
    assert beta.list_repository_events() == []
    assert beta.list_execution_events(conversation.id) == []
    with pytest.raises(KeyError, match="current tenant"):
        beta.add_execution_event(
            {
                "id": "cross-tenant-event",
                "conversation_id": conversation.id,
                "type": "done",
                "status": "succeeded",
                "payload": {},
                "created_at": "2026-08-13T00:00:00+00:00",
            }
        )

    beta.create_memory(
        {
            "type": "rule",
            "text": "Beta only",
            "source": "test",
            "confidence": 1,
            "status": "active",
            "project_id": "general",
        }
    )
    assert [item.text for item in alpha.list_memories()] == ["Alpha only"]
    assert [item.text for item in beta.list_memories()] == ["Beta only"]
    assert alpha.get_conversation(conversation.id) is not None
    assert [item.content for item in alpha.list_messages(conversation.id)] == ["Alpha message"]
    assert [item.title for item in alpha.list_artifacts()] == ["Alpha outcome"]
    assert alpha.list_repository_events()
    assert [item.id for item in alpha.list_execution_events(conversation.id)] == ["alpha-event"]


def test_delivery_modes_resolve_explicit_capabilities() -> None:
    community = build_product_profile(
        DeploymentMode.COMMUNITY,
        PlanId.COMMUNITY,
        "local",
        "local-owner",
    )
    cloud_free = build_product_profile(
        DeploymentMode.CLOUD,
        PlanId.CLOUD_FREE,
        "cloud-tenant",
        "cloud-owner",
        cloud_accounts_ready=True,
    )
    assert community.allows(Capability.LOCAL_MODELS)
    assert community.allows(Capability.MCP)
    assert not community.allows(Capability.MANAGED_MODELS)
    assert cloud_free.allows(Capability.MANAGED_MODELS)
    assert cloud_free.allows(Capability.DEVICE_SYNC)
    assert not cloud_free.allows(Capability.MCP)


def test_cloud_mode_fails_closed_until_account_identity_is_ready(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        cors_origins=("http://localhost:3000",),
        openai_models=("openai-test",),
        anthropic_models=("anthropic-test",),
        default_provider="openai",
        default_model="openai-test",
        deployment_mode=DeploymentMode.CLOUD,
        plan=PlanId.CLOUD_FREE,
        tenant_id="cloud-tenant",
        actor_id="cloud-owner",
    )
    with pytest.raises(RuntimeError, match="account identity service"):
        create_runtime(settings)


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
    conversation = database.create_conversation(
        provider="openai",
        model="openai-test",
        project_id="general",
        title="Audit conversation",
    )
    event = ExecutionEvent(
        id="event-new",
        type=EventType.TOOL_RESULT,
        status="succeeded",
        conversation_id=conversation.id,
        payload={"result": {"client_secret": "new-storage-secret", "value": "safe"}},
    )
    database.add_execution_event(event.model_dump(mode="json"))
    database.add_execution_event(
        {
            "id": "event-legacy",
            "conversation_id": conversation.id,
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

    restored = {item.id: item for item in database.list_execution_events(conversation.id)}
    assert restored["event-legacy"].payload["result"]["access_token"] == "[redacted]"
