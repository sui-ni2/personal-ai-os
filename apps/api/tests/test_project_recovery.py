from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from personal_ai_os.db import Database
from personal_ai_os.project_recovery import ProjectRecoveryService


def _seed_continuity(client: TestClient, project_id: str = "general", *, locked: bool = False) -> None:
    state = client.put(
        f"/api/projects/{project_id}/state/records",
        json={
            "namespace": "decision",
            "key": "next",
            "value": {"status": "reviewed"},
            "source": "recovery-test",
            "confidence": 0.9,
            "lock": locked,
            "expected_version": 0,
        },
    )
    assert state.status_code == 200
    workflow = client.post(
        f"/api/projects/{project_id}/workflows",
        json={
            "workflow_id": "research",
            "run_key": "sample",
            "steps": ["gather", "review", "publish"],
            "source": "recovery-test",
        },
    )
    assert workflow.status_code == 201
    advance = client.post(
        f"/api/projects/{project_id}/workflows/research/sample/advance",
        json={
            "next_step": "gather",
            "expected_version": 1,
            "evidence": {"receipt": "must-not-appear"},
            "source": "recovery-test",
        },
    )
    assert advance.status_code == 200


def _checkpoint(client: TestClient, project_id: str = "general") -> tuple[str, int]:
    started = client.post(f"/api/projects/{project_id}/recovery/sessions")
    assert started.status_code == 201
    session = started.json()
    checkpoint = client.post(
        f"/api/projects/{project_id}/recovery/sessions/{session['session_id']}/checkpoint",
        json={"expected_version": session["recovery_version"]},
    )
    assert checkpoint.status_code == 200
    return session["session_id"], checkpoint.json()["recovery_version"]


def test_normal_restart_is_clean_after_explicit_session_close(client: TestClient) -> None:
    _seed_continuity(client)
    session_id, version = _checkpoint(client)

    closed = client.post(
        f"/api/projects/general/recovery/sessions/{session_id}/close",
        json={"expected_version": version},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "clean"

    restart = client.get("/api/projects/general/recovery")
    assert restart.status_code == 200
    assert restart.json()["status"] == "clean"
    assert restart.json()["recovery_available"] is False


def test_active_checkpoint_is_recoverable_only_from_persisted_state(client: TestClient) -> None:
    _seed_continuity(client)
    session_id, version = _checkpoint(client)

    detected = client.get("/api/projects/general/recovery")
    assert detected.status_code == 200
    assert detected.json()["status"] == "recovery_available"
    assert detected.json()["session_id"] == session_id
    assert detected.json()["recovery_version"] == version
    assert "crash" not in detected.json()["message"].lower()

    preview = client.get(f"/api/projects/general/recovery/sessions/{session_id}/preview")
    assert preview.status_code == 200
    payload = preview.json()
    assert payload["snapshot"]["workflows"][0]["next_step"] == "review"
    assert "must-not-appear" not in preview.text

    confirmed = client.post(
        f"/api/projects/general/recovery/sessions/{session_id}/confirm",
        json={"expected_version": version},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "restored"
    assert confirmed.json()["resume_from"] == "authoritative_persisted_project_state"
    assert client.get("/api/projects/general/recovery").json()["status"] == "clean"


def test_partially_advanced_workflow_resumes_from_persisted_position(
    client: TestClient,
) -> None:
    workflow = client.post(
        "/api/projects/general/workflows",
        json={
            "workflow_id": "release",
            "run_key": "candidate",
            "steps": ["plan", "verify", "publish"],
            "source": "recovery-test",
        },
    )
    assert workflow.status_code == 201
    advanced = client.post(
        "/api/projects/general/workflows/release/candidate/advance",
        json={
            "next_step": "plan",
            "expected_version": 1,
            "evidence": {"note": "only the persisted position is authoritative"},
            "source": "recovery-test",
        },
    )
    assert advanced.status_code == 200
    session_id, version = _checkpoint(client)

    preview = client.get(f"/api/projects/general/recovery/sessions/{session_id}/preview")
    assert preview.status_code == 200
    assert preview.json()["snapshot"]["workflows"][0]["next_step"] == "verify"

    confirmed = client.post(
        f"/api/projects/general/recovery/sessions/{session_id}/confirm",
        json={"expected_version": version},
    )
    assert confirmed.status_code == 200
    persisted = client.get("/api/projects/general/workflows").json()["items"]
    assert persisted[0]["next_step"] == "verify"


def test_active_session_without_checkpoint_is_only_possibly_interrupted(client: TestClient) -> None:
    started = client.post("/api/projects/general/recovery/sessions")
    assert started.status_code == 201

    detected = client.get("/api/projects/general/recovery")
    assert detected.status_code == 200
    assert detected.json()["status"] == "possibly_interrupted"
    assert detected.json()["recovery_available"] is False
    assert "not treated as a crash" in detected.json()["message"]


def test_missing_or_empty_persisted_state_is_insufficient_evidence(client: TestClient) -> None:
    session_id, _ = _checkpoint(client)

    detected = client.get("/api/projects/general/recovery")
    assert detected.status_code == 200
    assert detected.json()["status"] == "insufficient_evidence"
    assert detected.json()["recovery_available"] is False

    preview = client.get(f"/api/projects/general/recovery/sessions/{session_id}/preview")
    assert preview.status_code == 409


def test_recovery_schema_migration_keeps_a_private_project_backup(client: TestClient, runtime) -> None:
    _seed_continuity(client)
    service = ProjectRecoveryService(
        runtime.database,
        data_dir=runtime.settings.data_dir,
        tenant_id=runtime.settings.tenant_id,
    )
    backup_dir = runtime.settings.data_dir / "backups" / "project-recovery"
    assert list(backup_dir.glob("recovery-v1-*.sqlite3")) == []

    _checkpoint(client)

    assert len(list(backup_dir.glob("recovery-v1-*.sqlite3"))) == 1


def test_stale_checkpoint_keeps_current_persisted_state_authoritative(client: TestClient) -> None:
    _seed_continuity(client)
    session_id, _ = _checkpoint(client)

    updated = client.put(
        "/api/projects/general/state/records",
        json={
            "namespace": "decision",
            "key": "next",
            "value": {"status": "updated-after-checkpoint"},
            "source": "recovery-test",
            "confidence": 0.9,
            "expected_version": 1,
        },
    )
    assert updated.status_code == 200

    preview = client.get(f"/api/projects/general/recovery/sessions/{session_id}/preview")
    assert preview.status_code == 200
    assert preview.json()["state_changed_since_checkpoint"] is True
    assert preview.json()["snapshot"]["states"][0]["value"] == {
        "status": "updated-after-checkpoint"
    }


def test_locked_state_is_previewed_but_never_mutated_by_recovery(client: TestClient) -> None:
    _seed_continuity(client, locked=True)
    session_id, version = _checkpoint(client)

    preview = client.get(f"/api/projects/general/recovery/sessions/{session_id}/preview")
    assert preview.status_code == 200
    assert preview.json()["snapshot"]["states"][0]["status"] == "locked"
    confirmed = client.post(
        f"/api/projects/general/recovery/sessions/{session_id}/confirm",
        json={"expected_version": version},
    )
    assert confirmed.status_code == 200
    state = client.get("/api/projects/general/state").json()["states"][0]
    assert state["status"] == "locked"
    assert state["version"] == 1


def test_recovery_confirmation_uses_optimistic_concurrency(client: TestClient) -> None:
    _seed_continuity(client)
    session_id, version = _checkpoint(client)

    first = client.post(
        f"/api/projects/general/recovery/sessions/{session_id}/confirm",
        json={"expected_version": version},
    )
    assert first.status_code == 200
    stale_retry = client.post(
        f"/api/projects/general/recovery/sessions/{session_id}/confirm",
        json={"expected_version": version},
    )
    assert stale_retry.status_code == 409
    assert "version mismatch" in stale_retry.json()["detail"]


def test_recovery_is_project_and_tenant_isolated(client: TestClient, runtime, tmp_path: Path) -> None:
    _seed_continuity(client, project_id="general")
    _checkpoint(client, project_id="general")

    other_project = client.get("/api/projects/p5/recovery")
    assert other_project.status_code == 200
    assert other_project.json()["status"] == "clean"

    other_database = Database(
        tmp_path / "other-tenant.sqlite3",
        tenant_id="tenant-other",
        actor_id="test-actor",
        deployment_mode="community",
    )
    other_service = ProjectRecoveryService(
        other_database,
        data_dir=runtime.settings.data_dir,
        tenant_id="tenant-other",
    )
    assert other_service.inspect("general")["status"] == "clean"
    assert other_service.state.storage_path("general") != ProjectRecoveryService(
        runtime.database,
        data_dir=runtime.settings.data_dir,
        tenant_id=runtime.settings.tenant_id,
    ).state.storage_path("general")
