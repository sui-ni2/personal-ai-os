from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi.testclient import TestClient
from personal_ai_os_core import Message

from personal_ai_os.main import create_app


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


def test_project_state_upsert_keeps_one_current_value(client: TestClient) -> None:
    for stage in ("input_ready", "locked"):
        response = client.put(
            "/api/projects/general/state/records",
            json={
                "namespace": "workflow",
                "key": "current",
                "value": {"stage": stage},
                "source": "test",
                "confidence": 1,
            },
        )
        assert response.status_code == 200

    states = client.get("/api/projects/general/state").json()["states"]
    workflow = [item for item in states if item["namespace"] == "workflow"]
    assert len(workflow) == 1
    assert workflow[0]["value"] == {"stage": "locked"}


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
