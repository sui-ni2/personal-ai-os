from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi.testclient import TestClient
from personal_ai_os_core import Message

from personal_ai_os.main import create_app
from personal_ai_os.project_state import ProjectStateService


def test_project_state_is_project_scoped_and_private(client: TestClient) -> None:
    saved = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "workflow",
            "key": "current",
            "value": {"stage": "review_done", "locked": True},
            "source": "test",
            "confidence": 1,
        },
    )
    assert saved.status_code == 200
    assert saved.json()["value"]["stage"] == "review_done"

    appended = client.post(
        "/api/projects/general/state/experience",
        json={
            "namespace": "review",
            "text": "Prefer verified prior records over reconstruction.",
            "source": "test",
            "confidence": 0.9,
        },
    )
    assert appended.status_code == 201

    snapshot = client.get("/api/projects/general/state")
    assert snapshot.status_code == 200
    assert snapshot.json()["states"][0]["namespace"] == "workflow"
    assert snapshot.json()["experiences"][0]["namespace"] == "review"

    other = client.get("/api/projects/p5/state")
    assert other.status_code == 200
    assert other.json()["states"] == []
    assert other.json()["experiences"] == []


def test_project_state_uses_separate_private_database_per_project(runtime) -> None:
    service = ProjectStateService(runtime.database)
    general_path = service.storage_path("general")
    p5_path = service.storage_path("p5")
    soccer_path = service.storage_path("soccer")

    assert general_path != p5_path != soccer_path
    assert "private" in general_path.parts
    assert general_path.name == "state.sqlite3"
    assert p5_path.name == "state.sqlite3"
    assert soccer_path.name == "state.sqlite3"

def test_project_state_upsert_keeps_one_current_value_and_history(client: TestClient) -> None:
    first = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "workflow",
            "key": "current",
            "value": {"stage": "input_ready"},
            "source": "test",
            "confidence": 1,
            "expected_version": 0,
        },
    )
    assert first.status_code == 200
    assert first.json()["version"] == 1

    second = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "workflow",
            "key": "current",
            "value": {"stage": "locked"},
            "source": "test",
            "confidence": 1,
            "expected_version": 1,
        },
    )
    assert second.status_code == 200
    assert second.json()["version"] == 2

    states = client.get("/api/projects/general/state").json()["states"]
    workflow = [item for item in states if item["namespace"] == "workflow"]
    assert len(workflow) == 1
    assert workflow[0]["value"] == {"stage": "locked"}

    history = client.get(
        "/api/projects/general/state/history?namespace=workflow&key=current"
    )
    assert history.status_code == 200
    assert len(history.json()["items"]) == 1
    assert history.json()["items"][0]["version"] == 1
    assert history.json()["items"][0]["value"] == {"stage": "input_ready"}


def test_locked_state_requires_explicit_supersede(client: TestClient) -> None:
    locked = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "formal",
            "key": "latest",
            "value": {"record": "synthetic-final"},
            "source": "test",
            "confidence": 1,
            "lock": True,
            "expected_version": 0,
        },
    )
    assert locked.status_code == 200
    assert locked.json()["status"] == "locked"
    assert locked.json()["version"] == 1

    accidental = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "formal",
            "key": "latest",
            "value": {"record": "synthetic-overwrite"},
            "source": "test",
            "confidence": 1,
            "expected_version": 1,
        },
    )
    assert accidental.status_code == 409

    explicit = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "formal",
            "key": "latest",
            "value": {"record": "synthetic-corrected"},
            "source": "test",
            "confidence": 1,
            "lock": True,
            "expected_version": 1,
            "supersede_locked": True,
        },
    )
    assert explicit.status_code == 200
    assert explicit.json()["status"] == "locked"
    assert explicit.json()["version"] == 2


def test_stale_window_cannot_overwrite_newer_state(client: TestClient) -> None:
    first = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "workflow",
            "key": "day",
            "value": {"stage": "reviewed"},
            "source": "window-a",
            "expected_version": 0,
        },
    )
    assert first.status_code == 200

    second = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "workflow",
            "key": "day",
            "value": {"stage": "a_locked"},
            "source": "window-b",
            "expected_version": 1,
        },
    )
    assert second.status_code == 200

    stale = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "workflow",
            "key": "day",
            "value": {"stage": "old-window-write"},
            "source": "window-a",
            "expected_version": 1,
        },
    )
    assert stale.status_code == 409


def test_new_conversation_receives_persistent_project_state(runtime, monkeypatch) -> None:
    captured: list[Message] = []
    provider = runtime.providers.get("openai")

    async def capture_stream(messages: list[Message], model: str) -> AsyncIterator[str]:
        captured.extend(messages)
        yield "ok"

    monkeypatch.setattr(provider, "stream", capture_stream)

    with TestClient(create_app(runtime=runtime)) as client:
        saved = client.put(
            "/api/projects/general/state/records",
            json={
                "namespace": "workflow",
                "key": "current",
                "value": {"stage": "history_bound"},
                "source": "test",
                "confidence": 1,
            },
        )
        assert saved.status_code == 200

        response = client.post(
            "/api/chat/stream",
            json={
                "provider": "openai",
                "model": "openai-test",
                "project_id": "general",
                "content": "Continue the project.",
            },
        )
        assert response.status_code == 200

    system_contents = [message.content for message in captured if message.role.value == "system"]
    persistent = next(text for text in system_contents if text.startswith("Persistent project state"))
    assert '"stage": "history_bound"' in persistent


def test_state_route_rejects_unknown_project(client: TestClient) -> None:
    response = client.get("/api/projects/not-a-project/state")
    assert response.status_code == 404
