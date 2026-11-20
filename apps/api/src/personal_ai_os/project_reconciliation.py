from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import Database
from .project_state import ProjectStateService
from .project_workflow import ProjectWorkflowService


class ProjectReconciliationService:
    """Bounded read-only preview of *stored* work, not external completion proof.

    Reuse the existing project/tenant-scoped source stores; do not construct
    project truth from a model claim, tool intent, or copied provider session.
    """

    def __init__(
        self,
        audit_database: Database,
        *,
        data_dir: Path | None = None,
        tenant_id: str | None = None,
    ) -> None:
        self.state = ProjectStateService(
            audit_database,
            data_dir=data_dir,
            tenant_id=tenant_id,
        )
        self.workflow = ProjectWorkflowService(
            audit_database,
            data_dir=data_dir,
            tenant_id=tenant_id,
        )

    def preview(self, project_id: str, *, limit: int = 20) -> dict[str, Any]:
        if not 1 <= limit <= 100:
            raise ValueError("Reconciliation preview limit must be between 1 and 100")

        state_count, states = self.state.list_state_metadata(project_id, limit=limit)
        workflow_count, workflows = self.workflow.list_workflow_metadata(
            project_id, limit=limit
        )
        return {
            "project_id": project_id,
            "read_at": datetime.now(timezone.utc).isoformat(),
            "evidence_scope": "PERSISTED_RECORDS_ONLY",
            "counts": {"states": state_count, "workflows": workflow_count},
            "truncated": state_count > limit or workflow_count > limit,
            "state_records": [
                {
                    "namespace": state["namespace"],
                    "key": state["key"],
                    "version": state["version"],
                    "storage_status": state["status"],
                    "evidence_label": "RECORDED",
                    "reason_code": "STORED_NOT_EXECUTION_PROOF",
                }
                for state in states
            ],
            "workflow_records": [
                {
                    "workflow_id": workflow["workflow_id"],
                    "run_key": workflow["run_key"],
                    "version": workflow["version"],
                    "recorded_status": workflow["status"],
                    "next_step": workflow["next_step"],
                    "evidence_label": "WORKFLOW_POSITION",
                    "external_execution": "UNVERIFIED",
                    "reason_code": "WORKFLOW_STATE_NOT_EXTERNAL_RECEIPT",
                }
                for workflow in workflows
            ],
        }
