from __future__ import annotations

from fastapi.testclient import TestClient

from personal_ai_os.project_state import ProjectStateService
from personal_ai_os.project_workflow import ProjectWorkflowService


def _put_state(client: TestClient, key: str, summary: str) -> None:
    response = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "task",
            "key": key,
            "value": {"summary": summary, "credentials": "DO_NOT_ECHO"},
            "source": "reconciliation-test",
            "expected_version": 0,
        },
    )
    assert response.status_code == 200


def test_reconciliation_preview_only_exposes_record_metadata(client: TestClient) -> None:
    _put_state(client, "step-one", "PRIVATE_STATE_VALUE")

    response = client.get("/api/projects/general/control-center/reconciliation-preview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "general"
    assert payload["evidence_scope"] == "PERSISTED_RECORDS_ONLY"
    assert payload["truncated"] is False
    assert payload["counts"]["states"] == 1
    record = payload["state_records"][0]
    assert record["evidence_label"] == "RECORDED"
    assert record["reason_code"] == "STORED_NOT_EXECUTION_PROOF"
    assert record["version"] == 1
    for sensitive in ("PRIVATE_STATE_VALUE", "DO_NOT_ECHO", "credentials", "source"):
        assert sensitive not in response.text

    other = client.get("/api/projects/p5/control-center/reconciliation-preview")
    assert other.status_code == 200
    assert other.json()["counts"] == {"states": 0, "workflows": 0}
    assert other.json()["state_records"] == []


def test_completed_workflow_does_not_imply_external_action(client: TestClient) -> None:
    created = client.post(
        "/api/projects/general/workflows",
        json={
            "workflow_id": "example",
            "run_key": "case-1",
            "steps": ["begin", "finish"],
            "source": "test",
        },
    )
    assert created.status_code == 201
    for step, version in (("begin", 1), ("finish", 2)):
        advanced = client.post(
            "/api/projects/general/workflows/example/case-1/advance",
            json={
                "next_step": step,
                "expected_version": version,
                "evidence": {"private_evidence": "SECRET_WORKFLOW_RECEIPT"},
                "source": "test",
            },
        )
        assert advanced.status_code == 200

    response = client.get("/api/projects/general/control-center/reconciliation-preview")
    assert response.status_code == 200
    record = response.json()["workflow_records"][0]
    assert record["recorded_status"] == "completed"
    assert record["evidence_label"] == "WORKFLOW_POSITION"
    assert record["external_execution"] == "UNVERIFIED"
    assert record["next_step"] is None
    assert "SECRET_WORKFLOW_RECEIPT" not in response.text


def test_preview_bounds_and_invalid_project_are_fail_closed(client: TestClient) -> None:
    _put_state(client, "one", "first")
    _put_state(client, "two", "second")
    response = client.get(
        "/api/projects/general/control-center/reconciliation-preview?limit=1"
    )
    assert response.status_code == 200
    assert response.json()["truncated"] is True
    assert response.json()["counts"]["states"] == 2
    assert len(response.json()["state_records"]) == 1

    for limit in (0, 101):
        result = client.get(
            f"/api/projects/general/control-center/reconciliation-preview?limit={limit}"
        )
        assert result.status_code == 422

    unknown = client.get(
        "/api/projects/no-such-project/control-center/reconciliation-preview"
    )
    assert unknown.status_code == 404


def test_preview_avoids_unbounded_private_state_and_workflow_loads(
    client: TestClient, monkeypatch
) -> None:
    for key in ("one", "two", "three"):
        _put_state(client, key, "PRIVATE_UNREAD_VALUE_" + key)
    for index in range(3):
        created = client.post(
            "/api/projects/general/workflows",
            json={
                "workflow_id": f"bounded-{index}",
                "run_key": "synthetic",
                "steps": ["start", "finish"],
                "source": "reconciliation-test",
            },
        )
        assert created.status_code == 201

    def forbidden_full_load(*args, **kwargs):
        raise AssertionError("Reconciliation must not load entire private state")

    monkeypatch.setattr(ProjectStateService, "list_state", forbidden_full_load)
    monkeypatch.setattr(ProjectStateService, "_state_from_row", forbidden_full_load)
    monkeypatch.setattr(ProjectWorkflowService, "list_workflows", forbidden_full_load)

    response = client.get(
        "/api/projects/general/control-center/reconciliation-preview?limit=1"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["counts"] == {"states": 3, "workflows": 3}
    assert payload["truncated"] is True
    assert len(payload["state_records"]) == 1
    assert len(payload["workflow_records"]) == 1
    assert payload["workflow_records"][0]["next_step"] == "start"
    assert "PRIVATE_UNREAD_VALUE" not in response.text
