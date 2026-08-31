from fastapi.testclient import TestClient


def _memory(client: TestClient, text: str, *, project_id: str | None = "general") -> dict[str, object]:
    response = client.post(
        "/api/memory",
        json={
            "type": "preference",
            "text": text,
            "source": "workbench-test",
            "confidence": 1,
            "project_id": project_id,
            "provenance": {"kind": "user_review"},
            "source_reference": "manual entry",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_memory_workbench_requires_review_and_resolves_conflicts_explicitly(client: TestClient) -> None:
    existing = _memory(client, "timezone=UTC")
    proposed = _memory(client, "timezone=Asia/Shanghai")
    assert proposed["status"] == "conflict_review_required"
    assert proposed["provenance"] == {"kind": "user_review"}
    conflicts = client.get(f"/api/memory/{proposed['id']}/conflicts")
    assert conflicts.status_code == 200
    assert [item["id"] for item in conflicts.json()["items"]] == [existing["id"]]

    direct_activation = client.patch(f"/api/memory/{proposed['id']}", json={"status": "active"})
    assert direct_activation.status_code == 200
    assert direct_activation.json()["status"] == "conflict_review_required"

    resolved = client.post(f"/api/memory/{proposed['id']}/resolve", json={"action": "replace"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "active"
    prior = client.get("/api/memory").json()["items"]
    assert next(item for item in prior if item["id"] == existing["id"])["status"] == "superseded"


def test_memory_workbench_can_reject_or_keep_both_with_explicit_scope(client: TestClient) -> None:
    global_memory = _memory(client, "editor=vim", project_id=None)
    rejected = _memory(client, "editor=emacs", project_id=None)
    assert rejected["status"] == "conflict_review_required"
    keep = client.post(f"/api/memory/{rejected['id']}/resolve", json={"action": "keep_existing"})
    assert keep.status_code == 200
    assert keep.json()["status"] == "rejected"

    scoped = _memory(client, "editor=emacs", project_id=None)
    both = client.post(
        f"/api/memory/{scoped['id']}/resolve",
        json={"action": "keep_both", "scope_project_id": "general"},
    )
    assert both.status_code == 200
    assert both.json()["status"] == "active"
    assert both.json()["project_id"] == "general"
    items = client.get("/api/memory").json()["items"]
    assert next(item for item in items if item["id"] == global_memory["id"])["status"] == "active"
