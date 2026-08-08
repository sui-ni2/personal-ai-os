from __future__ import annotations

from pathlib import Path

from personal_ai_os_core import Artifact, Conversation, MemoryRecord, Message, ProjectRegistry, RepositoryEvent
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
