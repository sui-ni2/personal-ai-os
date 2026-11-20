from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from personal_ai_os.governance import GovernanceService
from personal_ai_os.project_reconciliation import (
    classify_execution_metadata,
    classify_state_metadata,
    classify_workflow_metadata,
)
from personal_ai_os.project_state import ProjectStateService
from personal_ai_os.project_workflow import ProjectWorkflowService


def _put_state(client: TestClient, key: str, summary: str, *, expected_version: int = 0, lock: bool = False) -> None:
    response = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "task",
            "key": key,
            "value": {"summary": summary, "credentials": "DO_NOT_ECHO"},
            "source": "reconciliation-test",
            "expected_version": expected_version,
            "lock": lock,
        },
    )
    assert response.status_code == 200


def _create_workflow(client: TestClient, workflow_id: str, *, steps: list[str] | None = None) -> None:
    response = client.post(
        "/api/projects/general/workflows",
        json={
            "workflow_id": workflow_id,
            "run_key": "case-1",
            "steps": steps or ["begin", "finish"],
            "source": "reconciliation-test",
        },
    )
    assert response.status_code == 201


def _advance_workflow(client: TestClient, workflow_id: str, step: str = "begin") -> None:
    response = client.post(
        f"/api/projects/general/workflows/{workflow_id}/case-1/advance",
        json={
            "next_step": step,
            "expected_version": 1,
            "evidence": {"private_evidence": "SECRET_WORKFLOW_RECEIPT"},
            "source": "reconciliation-test",
        },
    )
    assert response.status_code == 200


def _private_project_db(runtime) -> sqlite3.Connection:
    service = ProjectStateService(
        runtime.database,
        data_dir=runtime.settings.data_dir,
        tenant_id=runtime.settings.tenant_id,
    )
    connection = sqlite3.connect(service.storage_path("general"))
    connection.row_factory = sqlite3.Row
    return connection


def test_reconciliation_preview_only_exposes_project_scoped_metadata(client: TestClient) -> None:
    _put_state(client, "step-one", "PRIVATE_STATE_VALUE")

    response = client.get("/api/projects/general/control-center/reconciliation-preview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "general"
    assert payload["evidence_scope"] == "PERSISTED_METADATA_ONLY"
    assert payload["truncated"] is False
    assert payload["counts"] == {"states": 1, "workflows": 0, "executions": 0}
    record = payload["state_records"][0]
    assert record["evidence_label"] == "RECORDED"
    assert record["reason_code"] == "STORED_NOT_EXECUTION_PROOF"
    assert record["history_integrity"] == "complete"
    assert record["version"] == 1
    assert payload["summary"]["by_label"]["RECORDED"] == 1
    assert len(payload["state_fingerprint"]) == 64
    for sensitive in ("PRIVATE_STATE_VALUE", "DO_NOT_ECHO", "credentials", "reconciliation-test", "SECRET_WORKFLOW_RECEIPT"):
        assert sensitive not in response.text

    other = client.get("/api/projects/p5/control-center/reconciliation-preview")
    assert other.status_code == 200
    assert other.json()["counts"] == {"states": 0, "workflows": 0, "executions": 0}
    assert other.json()["state_records"] == []
    assert other.json()["workflow_records"] == []
    assert other.json()["execution_records"] == []


def test_completed_workflow_does_not_imply_external_action(client: TestClient) -> None:
    _create_workflow(client, "example")
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
    assert record["transition_history_integrity"] == "complete"
    assert "SECRET_WORKFLOW_RECEIPT" not in response.text


def test_state_history_gaps_and_version_disagreement_are_distinguished(client: TestClient, runtime) -> None:
    for key in ("history-gap", "history-conflict"):
        _put_state(client, key, "first")
        _put_state(client, key, "second", expected_version=1)

    connection = _private_project_db(runtime)
    try:
        connection.execute(
            "DELETE FROM state_history WHERE namespace = 'task' AND key = 'history-gap'"
        )
        connection.execute(
            "UPDATE state_history SET version = 99 WHERE namespace = 'task' AND key = 'history-conflict'"
        )
    finally:
        connection.close()

    response = client.get("/api/projects/general/control-center/reconciliation-preview")
    assert response.status_code == 200
    records = {item["key"]: item for item in response.json()["state_records"]}
    assert records["history-gap"]["evidence_label"] == "INSUFFICIENT_EVIDENCE"
    assert records["history-gap"]["reason_code"] == "STATE_HISTORY_GAP"
    assert records["history-conflict"]["evidence_label"] == "CONFLICT"
    assert records["history-conflict"]["reason_code"] == "STATE_HISTORY_VERSION_CONFLICT"
    assert response.json()["needs_user_review"] is True


def test_workflow_transition_gaps_and_version_disagreement_are_distinguished(client: TestClient, runtime) -> None:
    _create_workflow(client, "transition-gap")
    _advance_workflow(client, "transition-gap")
    _create_workflow(client, "transition-conflict")
    _advance_workflow(client, "transition-conflict")

    connection = _private_project_db(runtime)
    try:
        connection.execute(
            "DELETE FROM workflow_transitions WHERE workflow_id = 'transition-gap'"
        )
        connection.execute(
            "UPDATE workflow_transitions SET version = 99 WHERE workflow_id = 'transition-conflict'"
        )
    finally:
        connection.close()

    response = client.get("/api/projects/general/control-center/reconciliation-preview")
    assert response.status_code == 200
    records = {item["workflow_id"]: item for item in response.json()["workflow_records"]}
    assert records["transition-gap"]["evidence_label"] == "INSUFFICIENT_EVIDENCE"
    assert records["transition-gap"]["reason_code"] == "WORKFLOW_TRANSITION_HISTORY_GAP"
    assert records["transition-conflict"]["evidence_label"] == "CONFLICT"
    assert records["transition-conflict"]["reason_code"] == "WORKFLOW_TRANSITION_VERSION_CONFLICT"


def test_unknown_external_outcome_requires_confirmation_without_exposing_details(client: TestClient, runtime) -> None:
    governance = GovernanceService(runtime.database)
    unknown = governance.create_execution_run(
        conversation_id="synthetic-unknown",
        project_id="general",
        provider="openai",
        model="test-model",
    )
    governance.update_execution_run(
        unknown,
        status="outcome_unknown",
        retry_status="retry_requires_confirmation",
        side_effect_status="outcome_unknown",
        detail={"private_error": "DO_NOT_ECHO_EXECUTION_DETAIL"},
    )
    completed = governance.create_execution_run(
        conversation_id="synthetic-completed",
        project_id="general",
        provider="openai",
        model="test-model",
    )
    governance.update_execution_run(
        completed,
        status="completed",
        retry_status="retry_safe",
        side_effect_status="completed",
        detail={"private_result": "DO_NOT_ECHO_COMPLETED_DETAIL"},
    )

    response = client.get("/api/projects/general/control-center/reconciliation-preview")
    assert response.status_code == 200
    records = {item["execution_id"]: item for item in response.json()["execution_records"]}
    assert records[unknown]["evidence_label"] == "NEEDS_CONFIRMATION"
    assert records[unknown]["reason_code"] == "EXTERNAL_SIDE_EFFECT_OUTCOME_UNKNOWN"
    assert records[completed]["evidence_label"] == "RECORDED"
    assert records[completed]["reason_code"] == "EXECUTION_RESULT_RECORDED_NOT_INDEPENDENT_PROOF"
    for sensitive in ("DO_NOT_ECHO_EXECUTION_DETAIL", "DO_NOT_ECHO_COMPLETED_DETAIL", "private_error", "private_result", "test-model", "openai"):
        assert sensitive not in response.text


def test_locked_state_is_recorded_but_requires_owner_review(client: TestClient) -> None:
    _put_state(client, "locked-record", "locked", lock=True)
    response = client.get("/api/projects/general/control-center/reconciliation-preview")
    record = next(item for item in response.json()["state_records"] if item["key"] == "locked-record")
    assert record["evidence_label"] == "RECORDED"
    assert record["reason_code"] == "LOCKED_STATE_REQUIRES_EXPLICIT_SUPERSESSION"
    assert record["review_required"] is True
    assert response.json()["needs_user_review"] is True


def test_preview_is_read_only_and_does_not_append_audit_or_transition_records(client: TestClient, runtime) -> None:
    _put_state(client, "read-only", "unchanged")
    _create_workflow(client, "read-only")
    private_before = _private_project_db(runtime)
    try:
        before_private = {
            table: private_before.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("current_state", "state_history", "workflows", "workflow_transitions")
        }
    finally:
        private_before.close()
    with runtime.database.connect() as connection:
        before_audit = connection.execute(
            "SELECT COUNT(*) FROM repository_events WHERE tenant_id = ? AND project_id = 'general'",
            (runtime.database.tenant_id,),
        ).fetchone()[0]
        before_execution_events = connection.execute(
            "SELECT COUNT(*) FROM execution_events WHERE tenant_id = ?",
            (runtime.database.tenant_id,),
        ).fetchone()[0]

    response = client.get("/api/projects/general/control-center/reconciliation-preview")
    assert response.status_code == 200

    private_after = _private_project_db(runtime)
    try:
        after_private = {
            table: private_after.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("current_state", "state_history", "workflows", "workflow_transitions")
        }
    finally:
        private_after.close()
    with runtime.database.connect() as connection:
        after_audit = connection.execute(
            "SELECT COUNT(*) FROM repository_events WHERE tenant_id = ? AND project_id = 'general'",
            (runtime.database.tenant_id,),
        ).fetchone()[0]
        after_execution_events = connection.execute(
            "SELECT COUNT(*) FROM execution_events WHERE tenant_id = ?",
            (runtime.database.tenant_id,),
        ).fetchone()[0]
    assert after_private == before_private
    assert after_audit == before_audit
    assert after_execution_events == before_execution_events


def test_preview_bounds_and_invalid_project_are_fail_closed(client: TestClient) -> None:
    _put_state(client, "one", "first")
    _put_state(client, "two", "second")
    response = client.get(
        "/api/projects/general/control-center/reconciliation-preview?limit=1"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["truncated"] is True
    assert payload["coverage"]["evidence_label"] == "INSUFFICIENT_EVIDENCE"
    assert payload["needs_user_review"] is True
    assert payload["counts"]["states"] == 2
    assert len(payload["state_records"]) == 1

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
        _create_workflow(client, f"bounded-{index}")

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
    assert payload["counts"] == {"states": 3, "workflows": 3, "executions": 0}
    assert payload["truncated"] is True
    assert len(payload["state_records"]) == 1
    assert len(payload["workflow_records"]) == 1
    assert payload["workflow_records"][0]["next_step"] == "begin"
    assert "PRIVATE_UNREAD_VALUE" not in response.text


def test_classifier_rejects_missing_or_inconsistent_metadata() -> None:
    state = classify_state_metadata({
        "namespace": "task", "key": "x", "version": 2, "status": "active",
        "history_count": 0, "history_distinct_versions": 0,
        "history_min_version": None, "history_max_version": None,
    })
    assert state["evidence_label"] == "INSUFFICIENT_EVIDENCE"

    workflow = classify_workflow_metadata({
        "workflow_id": "x", "run_key": "1", "version": 3, "status": "completed",
        "current_index": 0, "steps_valid": True, "step_count": 2, "next_step": "finish",
        "transition_count": 2, "transition_distinct_versions": 2,
        "transition_min_version": 2, "transition_max_version": 3,
    })
    assert workflow["evidence_label"] == "CONFLICT"

    execution = classify_execution_metadata({
        "id": "run", "status": "outcome_unknown", "retry_status": "retry_requires_confirmation",
        "side_effect_status": "outcome_unknown", "created_at": "now", "updated_at": "now",
    })
    assert execution["evidence_label"] == "NEEDS_CONFIRMATION"
