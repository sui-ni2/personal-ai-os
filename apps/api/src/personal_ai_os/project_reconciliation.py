from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import Database
from .project_state import ProjectStateService
from .project_workflow import ProjectWorkflowService


EVIDENCE_LABELS = (
    "RECORDED",
    "WORKFLOW_POSITION",
    "NEEDS_CONFIRMATION",
    "CONFLICT",
    "INSUFFICIENT_EVIDENCE",
)


def classify_state_metadata(record: dict[str, Any]) -> dict[str, Any]:
    """Classify a stored state row using only its version and history metadata."""
    version = int(record["version"])
    observed = int(record["history_count"])
    distinct = int(record["history_distinct_versions"])
    expected = version - 1
    minimum = record["history_min_version"]
    maximum = record["history_max_version"]

    label = "RECORDED"
    reason = "STORED_NOT_EXECUTION_PROOF"
    integrity = "complete"
    if version < 1:
        label, reason, integrity = "CONFLICT", "INVALID_STATE_VERSION", "conflict"
    elif (
        observed > expected
        or distinct != observed
        or (minimum is not None and int(minimum) < 1)
        or (maximum is not None and int(maximum) > expected)
    ):
        label, reason, integrity = "CONFLICT", "STATE_HISTORY_VERSION_CONFLICT", "conflict"
    elif observed < expected:
        label, reason, integrity = "INSUFFICIENT_EVIDENCE", "STATE_HISTORY_GAP", "missing"
    elif expected and (int(minimum or 0) != 1 or int(maximum or 0) != expected):
        label, reason, integrity = "CONFLICT", "STATE_HISTORY_VERSION_CONFLICT", "conflict"
    elif record["status"] not in {"active", "locked", "superseded"}:
        label, reason, integrity = "INSUFFICIENT_EVIDENCE", "UNKNOWN_STATE_STATUS", "unknown"
    elif record["status"] == "locked":
        reason = "LOCKED_STATE_REQUIRES_EXPLICIT_SUPERSESSION"
    elif record["status"] == "superseded":
        reason = "STATE_MARKED_SUPERSEDED"

    review_required = label in {"CONFLICT", "INSUFFICIENT_EVIDENCE"} or record["status"] == "locked"
    return {
        "namespace": record["namespace"],
        "key": record["key"],
        "version": version,
        "storage_status": record["status"],
        "history_integrity": integrity,
        "history_versions_expected": expected,
        "history_versions_observed": observed,
        "evidence_label": label,
        "reason_code": reason,
        "review_required": review_required,
    }


def classify_workflow_metadata(record: dict[str, Any]) -> dict[str, Any]:
    """Check the recorded workflow cursor against its version/transition ledger."""
    version = int(record["version"])
    current_index = int(record["current_index"])
    expected_version = current_index + 2
    observed = int(record["transition_count"])
    distinct = int(record["transition_distinct_versions"])
    expected_transitions = version - 1
    minimum = record["transition_min_version"]
    maximum = record["transition_max_version"]

    label = "WORKFLOW_POSITION"
    reason = "WORKFLOW_STATE_NOT_EXTERNAL_RECEIPT"
    integrity = "complete"
    if not record.get("steps_valid"):
        label, reason, integrity = "INSUFFICIENT_EVIDENCE", "WORKFLOW_DEFINITION_UNREADABLE", "unknown"
    elif version < 1 or current_index < -1 or current_index >= int(record["step_count"]):
        label, reason, integrity = "CONFLICT", "WORKFLOW_POSITION_OUT_OF_RANGE", "conflict"
    elif version != expected_version:
        label, reason, integrity = "CONFLICT", "WORKFLOW_VERSION_CURSOR_MISMATCH", "conflict"
    elif record["status"] not in {"active", "completed"}:
        label, reason, integrity = "CONFLICT", "UNKNOWN_WORKFLOW_STATUS", "conflict"
    else:
        should_be_completed = current_index == int(record["step_count"]) - 1
        if (record["status"] == "completed") != should_be_completed:
            label, reason, integrity = "CONFLICT", "WORKFLOW_STATUS_CURSOR_MISMATCH", "conflict"
        elif (
            observed > expected_transitions
            or distinct != observed
            or (minimum is not None and int(minimum) < 2)
            or (maximum is not None and int(maximum) > version)
        ):
            label, reason, integrity = "CONFLICT", "WORKFLOW_TRANSITION_VERSION_CONFLICT", "conflict"
        elif observed < expected_transitions:
            label, reason, integrity = "INSUFFICIENT_EVIDENCE", "WORKFLOW_TRANSITION_HISTORY_GAP", "missing"
        elif expected_transitions and (
            int(minimum or 0) != 2 or int(maximum or 0) != version
        ):
            label, reason, integrity = "CONFLICT", "WORKFLOW_TRANSITION_VERSION_CONFLICT", "conflict"

    return {
        "workflow_id": record["workflow_id"],
        "run_key": record["run_key"],
        "version": version,
        "recorded_status": record["status"],
        "next_step": record.get("next_step"),
        "transition_history_integrity": integrity,
        "transition_versions_expected": expected_transitions,
        "transition_versions_observed": observed,
        "evidence_label": label,
        "external_execution": "UNVERIFIED",
        "reason_code": reason,
        "review_required": label in {"CONFLICT", "INSUFFICIENT_EVIDENCE"},
    }


def classify_execution_metadata(record: dict[str, Any]) -> dict[str, Any]:
    """Classify only execution receipts that concern an external side effect/retry."""
    side_effect = record["side_effect_status"]
    retry = record["retry_status"]
    if side_effect in {"started", "outcome_unknown"}:
        label = "NEEDS_CONFIRMATION"
        reason = (
            "EXTERNAL_SIDE_EFFECT_OUTCOME_UNKNOWN"
            if side_effect == "outcome_unknown"
            else "EXTERNAL_SIDE_EFFECT_STILL_STARTED"
        )
    elif retry == "retry_requires_confirmation":
        label = "NEEDS_CONFIRMATION"
        reason = "RETRY_REQUIRES_EXPLICIT_CONFIRMATION"
    elif side_effect == "completed":
        label = "RECORDED"
        reason = "EXECUTION_RESULT_RECORDED_NOT_INDEPENDENT_PROOF"
    else:
        label = "INSUFFICIENT_EVIDENCE"
        reason = "UNKNOWN_EXTERNAL_EXECUTION_STATUS"

    return {
        "execution_id": record["id"],
        "status": record["status"],
        "retry_status": retry,
        "side_effect_status": side_effect,
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "evidence_label": label,
        "reason_code": reason,
        "review_required": label in {"NEEDS_CONFIRMATION", "INSUFFICIENT_EVIDENCE"},
    }


class ProjectReconciliationService:
    """Bounded, read-only evidence preview over existing project/tenant stores."""

    def __init__(
        self,
        audit_database: Database,
        *,
        data_dir: Path | None = None,
        tenant_id: str | None = None,
    ) -> None:
        self.audit_database = audit_database
        self.tenant_id = tenant_id or audit_database.tenant_id
        self.state = ProjectStateService(
            audit_database,
            data_dir=data_dir,
            tenant_id=self.tenant_id,
        )
        self.workflow = ProjectWorkflowService(
            audit_database,
            data_dir=data_dir,
            tenant_id=self.tenant_id,
        )

    def _execution_metadata(self, project_id: str, *, limit: int) -> tuple[int, list[dict[str, Any]]]:
        where = (
            "tenant_id = ? AND project_id = ? "
            "AND (side_effect_status <> 'not_started' OR retry_status = 'retry_requires_confirmation')"
        )
        params = (self.tenant_id, project_id)
        with self.audit_database.connect() as connection:
            total = int(connection.execute(
                f"SELECT COUNT(*) FROM execution_runs WHERE {where}", params
            ).fetchone()[0])
            rows = connection.execute(
                "SELECT id, status, retry_status, side_effect_status, created_at, updated_at "
                f"FROM execution_runs WHERE {where} ORDER BY updated_at DESC, id DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
        return total, [dict(row) for row in rows]

    def preview(self, project_id: str, *, limit: int = 20) -> dict[str, Any]:
        if not 1 <= limit <= 100:
            raise ValueError("Reconciliation preview limit must be between 1 and 100")

        state_count, states = self.state.list_state_metadata(project_id, limit=limit)
        workflow_count, workflows = self.workflow.list_workflow_metadata(
            project_id, limit=limit
        )
        execution_count, executions = self._execution_metadata(project_id, limit=limit)

        state_records = [classify_state_metadata(item) for item in states]
        workflow_records = [classify_workflow_metadata(item) for item in workflows]
        execution_records = [classify_execution_metadata(item) for item in executions]
        truncated = (
            state_count > limit
            or workflow_count > limit
            or execution_count > limit
        )
        by_label = {label: 0 for label in EVIDENCE_LABELS}
        for item in (*state_records, *workflow_records, *execution_records):
            by_label[item["evidence_label"]] += 1
        needs_user_review = truncated or any(
            item["review_required"]
            for item in (*state_records, *workflow_records, *execution_records)
        )
        fingerprint_input = {
            "counts": {
                "states": state_count,
                "workflows": workflow_count,
                "executions": execution_count,
            },
            "state_records": state_records,
            "workflow_records": workflow_records,
            "execution_records": execution_records,
            "truncated": truncated,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                fingerprint_input,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return {
            "project_id": project_id,
            "read_at": datetime.now(timezone.utc).isoformat(),
            "state_fingerprint": fingerprint,
            "evidence_scope": "PERSISTED_METADATA_ONLY",
            "counts": {
                "states": state_count,
                "workflows": workflow_count,
                "executions": execution_count,
            },
            "summary": {"by_label": by_label},
            "needs_user_review": needs_user_review,
            "truncated": truncated,
            "coverage": {
                "states": "partial" if state_count > limit else "complete",
                "workflows": "partial" if workflow_count > limit else "complete",
                "executions": "partial" if execution_count > limit else "complete",
                "evidence_label": "INSUFFICIENT_EVIDENCE" if truncated else "COMPLETE",
            },
            "state_records": state_records,
            "workflow_records": workflow_records,
            "execution_records": execution_records,
        }
