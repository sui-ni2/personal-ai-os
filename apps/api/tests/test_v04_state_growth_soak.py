from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from personal_ai_os.governance import GovernanceService, _arguments_digest
from personal_ai_os.project_recovery import ProjectRecoveryService
from personal_ai_os.project_state import ProjectStateService
from personal_ai_os.project_workflow import ProjectWorkflowService


RECORD_COUNT = 120
WORKFLOW_COUNT = 40


def _backup_and_restore_count(source_path, restored_path) -> int:
    source = sqlite3.connect(source_path)
    target = sqlite3.connect(restored_path)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    restored = sqlite3.connect(restored_path)
    try:
        return int(restored.execute("SELECT COUNT(*) FROM usage_ledger").fetchone()[0])
    finally:
        restored.close()


def test_v04_state_growth_soak_is_bounded_and_recovers_cleanly(runtime, tmp_path) -> None:
    """Exercise hundreds of synthetic records without a provider, credential, or user workspace."""
    runtime.database.migrate()
    project_id = "general"
    state = ProjectStateService(
        runtime.database, data_dir=runtime.settings.data_dir, tenant_id=runtime.settings.tenant_id
    )
    workflow = ProjectWorkflowService(
        runtime.database, data_dir=runtime.settings.data_dir, tenant_id=runtime.settings.tenant_id
    )
    governance = GovernanceService(runtime.database)
    governance.set_budget_policy(
        {
            "scope_type": "project",
            "scope_id": project_id,
            "period": "daily",
            "limit_tokens": 100_000,
            "warn_percent": 80,
            "hard_limit": True,
        }
    )

    for index in range(RECORD_COUNT):
        namespace = ("goal", "task", "decision", "outcome")[index % 4]
        state.put_state(
            project_id=project_id,
            namespace=namespace,
            key=f"soak-{index}",
            value={"fixture": index, "status": "synthetic"},
            source="v0.4-state-growth-soak",
            expected_version=0,
        )
        state.append_experience(
            project_id=project_id,
            namespace="soak",
            text=f"Synthetic bounded experience {index}",
            source="v0.4-state-growth-soak",
            confidence=1,
        )
        runtime.database.create_memory(
            {
                "type": "fact",
                "text": f"Synthetic memory {index}",
                "source": "v0.4-state-growth-soak",
                "confidence": 1,
                "project_id": project_id,
            }
        )
        governance.save_send_scope(
            {
                "project_id": project_id,
                "provider": "fixture-provider",
                "model": "fixture-model",
                "selected_files": [],
                "reviewed_memory_ids": [],
                "tool_availability": [],
                "context_categories": ["user_message", "project_metadata"],
                "approximate_context_tokens": 1,
                "context_precision": "ESTIMATED",
            },
            conversation_id=None,
            status="succeeded",
        )
        reservation = governance.reserve_budget(project_id, tokens=1, reason="v0.4-state-growth-soak")
        assert reservation["blocked"] is False
        governance.settle_budget_reservation(
            reservation["reservation_id"], status="committed" if index % 2 else "released"
        )
        governance.record_usage(
            conversation_id="soak-conversation",
            project_id=project_id,
            provider="fixture-provider",
            model="fixture-model",
            input_tokens=1,
            output_tokens=1,
            status="succeeded",
            latency_ms=1,
        )

    for index in range(WORKFLOW_COUNT):
        created = workflow.create_workflow(
            project_id=project_id,
            workflow_id=f"soak-workflow-{index}",
            run_key="run",
            steps=["prepare", "complete"],
            source="v0.4-state-growth-soak",
        )
        advanced = workflow.advance_workflow(
            project_id=project_id,
            workflow_id=created["workflow_id"],
            run_key=created["run_key"],
            next_step="prepare",
            expected_version=created["version"],
            evidence={"fixture": index},
            source="v0.4-state-growth-soak",
        )
        assert advanced["next_step"] == "complete"

    confirmation_id = "v04-soak-confirmation"
    arguments = {"fixture": "approved"}
    now = datetime.now(timezone.utc)
    with runtime.database.connect() as connection:
        connection.execute(
            "INSERT INTO tool_action_confirmations(id, tenant_id, actor_id, project_id, connector_id, tool_name, arguments_digest, preview_json, status, expires_at, created_at, confirmed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, '{}', 'confirmed', ?, ?, ?)",
            (
                confirmation_id,
                runtime.database.tenant_id,
                runtime.database.actor_id,
                project_id,
                "soak-connector",
                "external.fixture",
                _arguments_digest(arguments),
                (now + timedelta(minutes=10)).isoformat(),
                now.isoformat(),
                now.isoformat(),
            ),
        )
    assert governance.consume_tool_confirmation(
        confirmation_id=confirmation_id,
        project_id=project_id,
        connector_id="soak-connector",
        tool_name="external.fixture",
        arguments=arguments,
    )
    assert not governance.consume_tool_confirmation(
        confirmation_id=confirmation_id,
        project_id=project_id,
        connector_id="soak-connector",
        tool_name="external.fixture",
        arguments=arguments,
    )

    recovery = ProjectRecoveryService(
        runtime.database, data_dir=runtime.settings.data_dir, tenant_id=runtime.settings.tenant_id
    )
    session = recovery.start_session(project_id)
    checkpoint = recovery.checkpoint(
        project_id, session["session_id"], expected_version=session["recovery_version"]
    )
    closed = recovery.close_session(
        project_id, session["session_id"], expected_version=checkpoint["recovery_version"]
    )
    assert closed["status"] == "clean"
    assert recovery.inspect(project_id)["status"] == "clean"

    restored_usage_count = _backup_and_restore_count(
        runtime.database.path, tmp_path / "v04-state-growth-backup.sqlite3"
    )
    with runtime.database.connect() as connection:
        migration_version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        active_reservations = connection.execute(
            "SELECT COUNT(*) FROM budget_reservations WHERE tenant_id = ? AND status = 'active'",
            (runtime.database.tenant_id,),
        ).fetchone()[0]
        usage_count, usage_distinct = connection.execute(
            "SELECT COUNT(*), COUNT(DISTINCT id) FROM usage_ledger WHERE tenant_id = ?",
            (runtime.database.tenant_id,),
        ).fetchone()
        receipt_count = connection.execute(
            "SELECT COUNT(*) FROM send_scope_receipts WHERE tenant_id = ?", (runtime.database.tenant_id,)
        ).fetchone()[0]
        event_count = connection.execute(
            "SELECT COUNT(*) FROM repository_events WHERE tenant_id = ?", (runtime.database.tenant_id,)
        ).fetchone()[0]

    assert migration_version == 8
    assert integrity == "ok"
    assert active_reservations == 0
    assert usage_count == usage_distinct == RECORD_COUNT
    assert restored_usage_count == RECORD_COUNT
    assert receipt_count == RECORD_COUNT
    assert len(state.list_state(project_id)) == RECORD_COUNT
    assert len(state.list_experience(project_id)) == RECORD_COUNT
    assert len(runtime.database.list_memories()) == RECORD_COUNT
    assert len(workflow.list_workflows(project_id)) == WORKFLOW_COUNT
    assert RECORD_COUNT * 2 + WORKFLOW_COUNT * 2 <= event_count <= RECORD_COUNT * 3
