from __future__ import annotations

from fastapi.testclient import TestClient


def _seed_handoff(client: TestClient, project_id: str = "general") -> None:
    saved = client.put(
        f"/api/projects/{project_id}/state/records",
        json={
            "namespace": "decision",
            "key": "current",
            "value": {"status": "reviewed"},
            "source": "test-state",
            "confidence": 0.95,
            "expected_version": 0,
        },
    )
    assert saved.status_code == 200

    experience = client.post(
        f"/api/projects/{project_id}/state/experience",
        json={
            "namespace": "review",
            "text": "Keep verified state ahead of reconstruction.",
            "source": "test-review",
            "confidence": 0.9,
        },
    )
    assert experience.status_code == 201

    workflow = client.post(
        f"/api/projects/{project_id}/workflows",
        json={
            "workflow_id": "handoff-check",
            "run_key": "synthetic-run",
            "steps": ["review", "continue"],
            "source": "test-workflow",
        },
    )
    assert workflow.status_code == 201

    advanced = client.post(
        f"/api/projects/{project_id}/workflows/handoff-check/synthetic-run/advance",
        json={
            "next_step": "review",
            "expected_version": 1,
            "evidence": {"private_receipt": "must-not-appear-in-handoff"},
            "source": "test-workflow",
        },
    )
    assert advanced.status_code == 200


def test_compact_handoff_is_bounded_current_state_without_receipts(client: TestClient) -> None:
    _seed_handoff(client)

    response = client.get("/api/projects/general/handoff")
    assert response.status_code == 200
    payload = response.json()

    assert payload["project_id"] == "general"
    assert payload["mode"] == "compact"
    assert payload["truncated"] is False
    assert payload["counts"] == {"states": 1, "experiences": 1, "workflows": 1}
    assert payload["resume"] == {
        "recorded_workflows": {"active": 1, "completed": 0, "other": 0},
        "next_steps": [
            {"workflow_id": "handoff-check", "run_key": "synthetic-run", "next_step": "continue", "version": 2}
        ],
        "coverage": "complete",
    }

    state = payload["states"][0]
    assert state["value"] == {"status": "reviewed"}
    assert "source" not in state
    assert "confidence" not in state

    experience = payload["experiences"][0]
    assert experience["text"] == "Keep verified state ahead of reconstruction."
    assert "source" not in experience

    workflow = payload["workflows"][0]
    assert workflow["completed_steps"] == ["review"]
    assert workflow["next_step"] == "continue"
    assert "steps" not in workflow
    assert "source" not in workflow

    serialized = response.text
    assert "private_receipt" not in serialized
    assert "must-not-appear-in-handoff" not in serialized


def test_full_handoff_keeps_rich_current_records_but_not_transition_evidence(client: TestClient) -> None:
    _seed_handoff(client)

    response = client.get("/api/projects/general/handoff?mode=full")
    assert response.status_code == 200
    payload = response.json()

    assert payload["mode"] == "full"
    assert payload["states"][0]["source"] == "test-state"
    assert payload["states"][0]["confidence"] == 0.95
    assert payload["experiences"][0]["source"] == "test-review"
    assert payload["workflows"][0]["steps"] == ["review", "continue"]
    assert payload["workflows"][0]["source"] == "test-workflow"

    serialized = response.text
    assert "private_receipt" not in serialized
    assert "must-not-appear-in-handoff" not in serialized


def test_resume_inventory_respects_persisted_workflow_completion(client: TestClient) -> None:
    _seed_handoff(client)
    before = client.get("/api/projects/general/handoff").json()["resume"]
    assert before["recorded_workflows"]["completed"] == 0
    assert len(before["next_steps"]) == 1

    advance = client.post(
        "/api/projects/general/workflows/handoff-check/synthetic-run/advance",
        json={
            "next_step": "continue",
            "expected_version": 2,
            "evidence": {"private_receipt": "not-in-resume"},
            "source": "test-workflow",
        },
    )
    assert advance.status_code == 200

    response = client.get("/api/projects/general/handoff")
    assert response.status_code == 200
    resume = response.json()["resume"]
    assert resume["recorded_workflows"] == {"active": 0, "completed": 1, "other": 0}
    assert resume["next_steps"] == []
    assert resume["coverage"] == "complete"
    assert "not-in-resume" not in response.text


def test_handoff_is_project_scoped(client: TestClient) -> None:
    _seed_handoff(client, project_id="general")

    other = client.get("/api/projects/p5/handoff")
    assert other.status_code == 200
    assert other.json()["counts"] == {"states": 0, "experiences": 0, "workflows": 0}
    assert other.json()["states"] == []
    assert other.json()["experiences"] == []
    assert other.json()["workflows"] == []


def test_handoff_rejects_unknown_project_and_invalid_mode(client: TestClient) -> None:
    unknown = client.get("/api/projects/not-a-project/handoff")
    assert unknown.status_code == 404

    invalid = client.get("/api/projects/general/handoff?mode=unbounded")
    assert invalid.status_code == 422
