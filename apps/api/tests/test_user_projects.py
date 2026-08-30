from __future__ import annotations

from fastapi.testclient import TestClient

from personal_ai_os.main import create_app


def test_user_can_create_domain_neutral_project_and_use_private_state(client: TestClient) -> None:
    created = client.post(
        "/api/projects",
        json={"name": "Long-running research", "description": "A reproducible non-sensitive research workflow."},
    )
    assert created.status_code == 201
    project = created.json()
    assert project["id"] == "long-running-research"
    assert project["icon"] == "folder"

    state = client.put(
        f"/api/projects/{project['id']}/state/records",
        json={
            "namespace": "task",
            "key": "next",
            "value": {"title": "Review sources"},
            "source": "user-project-test",
            "expected_version": 0,
        },
    )
    assert state.status_code == 200
    assert state.json()["project_id"] == project["id"]


def test_user_project_rehydrates_after_runtime_restart(runtime_factory: object) -> None:
    factory = runtime_factory
    first_runtime = factory()
    with TestClient(create_app(runtime=first_runtime)) as first_client:
        created = first_client.post(
            "/api/projects",
            json={"name": "Durable build", "description": "A general build workflow."},
        )
        assert created.status_code == 201
        project_id = created.json()["id"]

    second_runtime = factory()
    with TestClient(create_app(runtime=second_runtime)) as second_client:
        listed = second_client.get("/api/projects")
        assert listed.status_code == 200
        assert project_id in {item["id"] for item in listed.json()["items"]}
