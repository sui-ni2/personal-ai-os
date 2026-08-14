from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from .db import Database
from .project_state import ProjectStateService


MAX_WORKFLOW_CONTEXT = 20


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectWorkflowConflict(RuntimeError):
    pass


class ProjectWorkflowService:
    """Strict private workflow state machine stored in the project's private SQLite file.

    The engine is domain-neutral. Real workflow IDs, run keys, step names and evidence are runtime
    data and must not be committed to the public repository.
    """

    def __init__(
        self,
        audit_database: Database,
        *,
        data_dir: Path | None = None,
        tenant_id: str | None = None,
    ) -> None:
        self.audit_database = audit_database
        self.state = ProjectStateService(
            audit_database,
            data_dir=data_dir,
            tenant_id=tenant_id,
        )

    def storage_path(self, project_id: str) -> Path:
        return self.state.storage_path(project_id)

    @contextmanager
    def _connect(self, project_id: str) -> Iterator[sqlite3.Connection]:
        path = self.storage_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            self._migrate(connection)
            yield connection
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT NOT NULL,
                run_key TEXT NOT NULL,
                steps_json TEXT NOT NULL,
                current_index INTEGER NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (workflow_id, run_key)
            );
            CREATE INDEX IF NOT EXISTS workflows_updated
                ON workflows(updated_at DESC);
            CREATE TABLE IF NOT EXISTS workflow_transitions (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                run_key TEXT NOT NULL,
                version INTEGER NOT NULL,
                step TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS workflow_transitions_lookup
                ON workflow_transitions(workflow_id, run_key, version);
            """
        )

    @staticmethod
    def _row_to_workflow(row: sqlite3.Row) -> dict[str, Any]:
        steps = json.loads(row["steps_json"])
        index = int(row["current_index"])
        current_step = steps[index] if 0 <= index < len(steps) else None
        next_step = steps[index + 1] if index + 1 < len(steps) else None
        return {
            "workflow_id": row["workflow_id"],
            "run_key": row["run_key"],
            "steps": steps,
            "completed_steps": steps[: index + 1],
            "current_step": current_step,
            "next_step": next_step,
            "version": row["version"],
            "status": row["status"],
            "source": row["source"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def create_workflow(
        self,
        *,
        project_id: str,
        workflow_id: str,
        run_key: str,
        steps: list[str],
        source: str,
    ) -> dict[str, Any]:
        if not steps:
            raise ProjectWorkflowConflict("Workflow must contain at least one step")
        if len(set(steps)) != len(steps):
            raise ProjectWorkflowConflict("Workflow steps must be unique")
        now = _now()
        with self._connect(project_id) as connection:
            existing = connection.execute(
                "SELECT 1 FROM workflows WHERE workflow_id = ? AND run_key = ?",
                (workflow_id, run_key),
            ).fetchone()
            if existing:
                raise ProjectWorkflowConflict(
                    f"Workflow {workflow_id}/{run_key} already exists"
                )
            connection.execute(
                "INSERT INTO workflows(workflow_id, run_key, steps_json, current_index, version, status, source, created_at, updated_at) "
                "VALUES (?, ?, ?, -1, 1, 'active', ?, ?, ?)",
                (
                    workflow_id,
                    run_key,
                    json.dumps(steps, ensure_ascii=False, separators=(",", ":")),
                    source,
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM workflows WHERE workflow_id = ? AND run_key = ?",
                (workflow_id, run_key),
            ).fetchone()
            assert row is not None
            result = self._row_to_workflow(row)

        self.audit_database.add_repository_event(
            event_type="project_workflow.created",
            summary="Created private project workflow",
            project_id=project_id,
            details={"workflow_id": workflow_id, "run_key": run_key, "version": 1},
        )
        return {"project_id": project_id, **result}

    def get_workflow(
        self,
        project_id: str,
        workflow_id: str,
        run_key: str,
    ) -> dict[str, Any] | None:
        with self._connect(project_id) as connection:
            row = connection.execute(
                "SELECT * FROM workflows WHERE workflow_id = ? AND run_key = ?",
                (workflow_id, run_key),
            ).fetchone()
        return self._row_to_workflow(row) if row else None

    def list_workflows(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect(project_id) as connection:
            rows = connection.execute(
                "SELECT * FROM workflows ORDER BY updated_at DESC"
            ).fetchall()
        return [self._row_to_workflow(row) for row in rows]

    def advance_workflow(
        self,
        *,
        project_id: str,
        workflow_id: str,
        run_key: str,
        next_step: str,
        expected_version: int,
        evidence: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        now = _now()
        with self._connect(project_id) as connection:
            row = connection.execute(
                "SELECT * FROM workflows WHERE workflow_id = ? AND run_key = ?",
                (workflow_id, run_key),
            ).fetchone()
            if row is None:
                raise ProjectWorkflowConflict(
                    f"Workflow {workflow_id}/{run_key} does not exist"
                )
            current = self._row_to_workflow(row)
            if current["status"] == "completed":
                raise ProjectWorkflowConflict(
                    f"Workflow {workflow_id}/{run_key} is already completed"
                )
            if int(current["version"]) != expected_version:
                raise ProjectWorkflowConflict(
                    f"Workflow {workflow_id}/{run_key} version mismatch: current={current['version']}, expected={expected_version}"
                )
            required_step = current["next_step"]
            if next_step != required_step:
                raise ProjectWorkflowConflict(
                    f"Workflow {workflow_id}/{run_key} cannot advance to {next_step!r}; required next step is {required_step!r}"
                )

            new_index = int(row["current_index"]) + 1
            steps = current["steps"]
            new_version = expected_version + 1
            new_status = "completed" if new_index == len(steps) - 1 else "active"
            connection.execute(
                "UPDATE workflows SET current_index = ?, version = ?, status = ?, source = ?, updated_at = ? "
                "WHERE workflow_id = ? AND run_key = ?",
                (
                    new_index,
                    new_version,
                    new_status,
                    source,
                    now,
                    workflow_id,
                    run_key,
                ),
            )
            connection.execute(
                "INSERT INTO workflow_transitions(id, workflow_id, run_key, version, step, evidence_json, source, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    workflow_id,
                    run_key,
                    new_version,
                    next_step,
                    json.dumps(evidence, ensure_ascii=False, separators=(",", ":")),
                    source,
                    now,
                ),
            )
            updated = connection.execute(
                "SELECT * FROM workflows WHERE workflow_id = ? AND run_key = ?",
                (workflow_id, run_key),
            ).fetchone()
            assert updated is not None
            result = self._row_to_workflow(updated)

        self.audit_database.add_repository_event(
            event_type="project_workflow.advanced",
            summary="Advanced private project workflow",
            project_id=project_id,
            details={
                "workflow_id": workflow_id,
                "run_key": run_key,
                "step": next_step,
                "version": result["version"],
                "status": result["status"],
            },
        )
        return {"project_id": project_id, **result}

    def list_transitions(
        self,
        project_id: str,
        workflow_id: str,
        run_key: str,
    ) -> list[dict[str, Any]]:
        with self._connect(project_id) as connection:
            rows = connection.execute(
                "SELECT * FROM workflow_transitions WHERE workflow_id = ? AND run_key = ? ORDER BY version",
                (workflow_id, run_key),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "workflow_id": row["workflow_id"],
                "run_key": row["run_key"],
                "version": row["version"],
                "step": row["step"],
                "evidence": json.loads(row["evidence_json"]),
                "source": row["source"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def context_json(self, project_id: str) -> str:
        workflows = self.list_workflows(project_id)[:MAX_WORKFLOW_CONTEXT]
        compact = [
            {
                "workflow_id": item["workflow_id"],
                "run_key": item["run_key"],
                "completed_steps": item["completed_steps"],
                "current_step": item["current_step"],
                "next_step": item["next_step"],
                "version": item["version"],
                "status": item["status"],
            }
            for item in workflows
        ]
        return json.dumps({"project_id": project_id, "workflows": compact}, ensure_ascii=False)
