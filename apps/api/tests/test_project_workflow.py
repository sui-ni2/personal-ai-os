from __future__ import annotations

import base64
import hashlib
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient
from personal_ai_os_core import Message

from personal_ai_os.main import create_app
from personal_ai_os.project_workflow import ProjectWorkflowService


def _create_workflow(client: TestClient, project_id: str = "general"):
    response = client.post(
        f"/api/projects/{project_id}/workflows",
        json={
            "workflow_id": "daily",
            "run_key": "synthetic-run",
            "steps": ["review", "input", "formal", "complete"],
            "source": "test",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_workflow_cannot_skip_required_step(client: TestClient) -> None:
    created = _create_workflow(client)
    assert created["version"] == 1
    assert created["completed_steps"] == []
    assert created["next_step"] == "review"

    skipped = client.post(
        "/api/projects/general/workflows/daily/synthetic-run/advance",
        json={
            "next_step": "formal",
            "expected_version": 1,
            "evidence": {"artifact": "synthetic"},
            "source": "window-a",
        },
    )
    assert skipped.status_code == 409

    advanced = client.post(
        "/api/projects/general/workflows/daily/synthetic-run/advance",
        json={
            "next_step": "review",
            "expected_version": 1,
            "evidence": {"artifact": "synthetic-review"},
            "source": "window-a",
        },
    )
    assert advanced.status_code == 200
    assert advanced.json()["version"] == 2
    assert advanced.json()["completed_steps"] == ["review"]
    assert advanced.json()["next_step"] == "input"


def test_stale_window_cannot_advance_workflow(client: TestClient) -> None:
    _create_workflow(client)
    first = client.post(
        "/api/projects/general/workflows/daily/synthetic-run/advance",
        json={
            "next_step": "review",
            "expected_version": 1,
            "evidence": {"source": "verified"},
            "source": "window-b",
        },
    )
    assert first.status_code == 200

    stale = client.post(
        "/api/projects/general/workflows/daily/synthetic-run/advance",
        json={
            "next_step": "input",
            "expected_version": 1,
            "evidence": {"source": "stale-window"},
            "source": "window-a",
        },
    )
    assert stale.status_code == 409


def test_workflow_completion_and_transition_receipts(client: TestClient) -> None:
    _create_workflow(client)
    version = 1
    for step in ["review", "input", "formal", "complete"]:
        response = client.post(
            "/api/projects/general/workflows/daily/synthetic-run/advance",
            json={
                "next_step": step,
                "expected_version": version,
                "evidence": {"receipt": f"synthetic-{step}"},
                "source": "test",
            },
        )
        assert response.status_code == 200
        version += 1

    final = client.get(
        "/api/projects/general/workflows/daily/synthetic-run"
    ).json()
    assert final["status"] == "completed"
    assert final["next_step"] is None
    assert final["completed_steps"] == ["review", "input", "formal", "complete"]

    transitions = client.get(
        "/api/projects/general/workflows/daily/synthetic-run/transitions"
    )
    assert transitions.status_code == 200
    items = transitions.json()["items"]
    assert [item["step"] for item in items] == ["review", "input", "formal", "complete"]
    assert items[2]["evidence"] == {"receipt": "synthetic-formal"}

    extra = client.post(
        "/api/projects/general/workflows/daily/synthetic-run/advance",
        json={
            "next_step": "complete",
            "expected_version": version,
            "evidence": {},
            "source": "test",
        },
    )
    assert extra.status_code == 409


def test_workflow_storage_is_physically_project_scoped(runtime) -> None:
    service = ProjectWorkflowService(
        runtime.database,
        data_dir=runtime.settings.data_dir,
        tenant_id=runtime.settings.tenant_id,
    )
    assert service.storage_path("soccer") != service.storage_path("p5")
    assert service.storage_path("soccer").parent.name == base64.urlsafe_b64encode(
        hashlib.sha256(b"soccer").digest()[:16]
    ).decode("ascii").rstrip("=")
    assert service.storage_path("p5").parent.name == base64.urlsafe_b64encode(
        hashlib.sha256(b"p5").digest()[:16]
    ).decode("ascii").rstrip("=")


def test_workflow_does_not_leak_into_generic_memory(client: TestClient) -> None:
    _create_workflow(client, project_id="soccer")
    generic_memory = client.get("/api/memory").json()["items"]
    assert all(item.get("project_id") != "soccer" for item in generic_memory)

    p5 = client.get("/api/projects/p5/workflows")
    assert p5.status_code == 200
    assert p5.json()["items"] == []


def test_new_conversation_receives_workflow_gate_context(runtime, monkeypatch) -> None:
    captured: list[Message] = []
    provider = runtime.providers.get("openai")

    async def capture_stream(messages: list[Message], model: str) -> AsyncIterator[str]:
        captured.extend(messages)
        yield "ok"

    monkeypatch.setattr(provider, "stream", capture_stream)

    with TestClient(create_app(runtime=runtime)) as client:
        _create_workflow(client)
        advanced = client.post(
            "/api/projects/general/workflows/daily/synthetic-run/advance",
            json={
                "next_step": "review",
                "expected_version": 1,
                "evidence": {"receipt": "synthetic-review"},
                "source": "test",
            },
        )
        assert advanced.status_code == 200

        response = client.post(
            "/api/chat/stream",
            json={
                "provider": "openai",
                "model": "openai-test",
                "project_id": "general",
                "content": "Continue this project from its saved workflow.",
            },
        )
        assert response.status_code == 200

    system_contents = [message.content for message in captured if message.role.value == "system"]
    workflow = next(
        text for text in system_contents if text.startswith("Persistent project workflow gates")
    )
    assert '"completed_steps": ["review"]' in workflow
    assert '"next_step": "input"' in workflow


def test_workflow_route_rejects_unknown_project(client: TestClient) -> None:
    response = client.get("/api/projects/not-a-project/workflows")
    assert response.status_code == 404
