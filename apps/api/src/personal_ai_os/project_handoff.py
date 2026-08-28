from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from .db import Database
from .project_state import ProjectStateService
from .project_workflow import ProjectWorkflowService


HandoffMode = Literal["compact", "full"]

MAX_COMPACT_STATES = 20
MAX_COMPACT_EXPERIENCES = 20
MAX_COMPACT_WORKFLOWS = 10
MAX_FULL_STATES = 200
MAX_FULL_EXPERIENCES = 200
MAX_FULL_WORKFLOWS = 100


class ProjectHandoffService:
    """Build bounded, read-only project handoff snapshots from private continuity state.

    Handoffs reuse the existing project-scoped state/workflow stores. They do not copy provider
    sessions, state history, workflow transition evidence, credentials, or generic Memory records.
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

    @staticmethod
    def _compact_state(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "namespace": item["namespace"],
            "key": item["key"],
            "value": item["value"],
            "version": item["version"],
            "status": item["status"],
            "updated_at": item["updated_at"],
        }

    @staticmethod
    def _compact_experience(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "namespace": item["namespace"],
            "text": item["text"],
            "confidence": item["confidence"],
            "created_at": item["created_at"],
        }

    @staticmethod
    def _compact_workflow(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "workflow_id": item["workflow_id"],
            "run_key": item["run_key"],
            "completed_steps": item["completed_steps"],
            "current_step": item["current_step"],
            "next_step": item["next_step"],
            "version": item["version"],
            "status": item["status"],
            "updated_at": item["updated_at"],
        }

    def build(self, project_id: str, *, mode: HandoffMode = "compact") -> dict[str, Any]:
        states = self.state.list_state(project_id)
        experiences = self.state.list_experience(project_id)
        workflows = self.workflow.list_workflows(project_id)

        if mode == "compact":
            state_limit = MAX_COMPACT_STATES
            experience_limit = MAX_COMPACT_EXPERIENCES
            workflow_limit = MAX_COMPACT_WORKFLOWS
            selected_states = [
                self._compact_state(item) for item in states[:state_limit]
            ]
            selected_experiences = [
                self._compact_experience(item)
                for item in experiences[:experience_limit]
            ]
            selected_workflows = [
                self._compact_workflow(item)
                for item in workflows[:workflow_limit]
            ]
        elif mode == "full":
            state_limit = MAX_FULL_STATES
            experience_limit = MAX_FULL_EXPERIENCES
            workflow_limit = MAX_FULL_WORKFLOWS
            selected_states = states[:state_limit]
            selected_experiences = experiences[:experience_limit]
            selected_workflows = workflows[:workflow_limit]
        else:
            raise ValueError(f"Unsupported handoff mode: {mode}")

        truncated = (
            len(states) > state_limit
            or len(experiences) > experience_limit
            or len(workflows) > workflow_limit
        )
        return {
            "project_id": project_id,
            "mode": mode,
            "counts": {
                "states": len(states),
                "experiences": len(experiences),
                "workflows": len(workflows),
            },
            "truncated": truncated,
            "states": selected_states,
            "experiences": selected_experiences,
            "workflows": selected_workflows,
        }
