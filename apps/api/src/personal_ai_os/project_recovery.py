from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from .db import Database
from .project_handoff import ProjectHandoffService
from .project_state import ProjectStateService
from .project_workflow import ProjectWorkflowService


RECOVERY_CLEAN = "clean"
RECOVERY_POSSIBLY_INTERRUPTED = "possibly_interrupted"
RECOVERY_AVAILABLE = "recovery_available"
RECOVERY_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
RECOVERY_STATUSES = {
    RECOVERY_CLEAN,
    RECOVERY_POSSIBLY_INTERRUPTED,
    RECOVERY_AVAILABLE,
    RECOVERY_INSUFFICIENT_EVIDENCE,
}

_SESSION_ACTIVE = "active"
_SESSION_CLOSED = "closed"
_SESSION_RESTORED = "restored"
_CHECKPOINT_KIND = "persisted_continuity_checkpoint"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectRecoveryConflict(RuntimeError):
    pass


class ProjectRecoveryService:
    """Guide explicit project recovery from private persisted state only.

    A recovery session contains a bounded metadata-only checkpoint. It never stores provider
    sessions, conversation text, state values, transition receipts, credentials, or reasoning.
    An active session is evidence that a client did not record a clean close; it is deliberately
    not treated as proof that a normal window close was a crash.
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
        self.workflow = ProjectWorkflowService(
            audit_database,
            data_dir=data_dir,
            tenant_id=tenant_id,
        )
        self.handoff = ProjectHandoffService(
            audit_database,
            data_dir=data_dir,
            tenant_id=tenant_id,
        )

    @contextmanager
    def _connect(self, project_id: str) -> Iterator[sqlite3.Connection]:
        path = self._storage_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            self._migrate(connection)
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _storage_path(self, project_id: str) -> Path:
        """Return a fixed-format recovery metadata path without embedding a project ID.

        Recovery sessions are separate from the authoritative project-state database. The
        registry check at the route boundary authorizes the project; the one-way scope keeps
        an untrusted identifier out of every filesystem path while preserving physical
        tenant/project isolation.
        """

        tenant_scope = hashlib.sha256(self.state.tenant_id.encode("utf-8")).hexdigest()[:12]
        project_scope = hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:16]
        return (
            self.state.data_dir
            / "recovery"
            / f"{tenant_scope}-{project_scope}.sqlite3"
        )

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS project_recovery_schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        applied = {
            row["version"]
            for row in connection.execute(
                "SELECT version FROM project_recovery_schema_migrations"
            )
        }
        if 1 in applied:
            return
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS recovery_sessions (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                version INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                closed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS recovery_sessions_status_updated
                ON recovery_sessions(status, updated_at DESC);
            """
        )
        connection.execute(
            "INSERT INTO project_recovery_schema_migrations(version, applied_at) VALUES (1, ?)",
            (_now(),),
        )

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "status": row["status"],
            "evidence": json.loads(row["evidence_json"]),
            "version": int(row["version"]),
            "started_at": row["started_at"],
            "updated_at": row["updated_at"],
            "closed_at": row["closed_at"],
        }

    def _get_session(self, project_id: str, session_id: str) -> dict[str, Any] | None:
        with self._connect(project_id) as connection:
            row = connection.execute(
                "SELECT * FROM recovery_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return self._row_to_session(row) if row else None

    def _latest_active_session(self, project_id: str) -> dict[str, Any] | None:
        with self._connect(project_id) as connection:
            row = connection.execute(
                "SELECT * FROM recovery_sessions WHERE status = ? "
                "ORDER BY updated_at DESC, id DESC LIMIT 1",
                (_SESSION_ACTIVE,),
            ).fetchone()
        return self._row_to_session(row) if row else None

    def _continuity_metadata(self, project_id: str) -> dict[str, Any]:
        state_refs = [
            {
                "namespace": item["namespace"],
                "key": item["key"],
                "version": item["version"],
                "status": item["status"],
                "updated_at": item["updated_at"],
            }
            for item in self.state.list_state(project_id)
        ]
        experience_refs = [
            {
                "id": item["id"],
                "namespace": item["namespace"],
                "confidence": item["confidence"],
                "created_at": item["created_at"],
            }
            for item in self.state.list_experience(project_id)
        ]
        workflow_refs = [
            {
                "workflow_id": item["workflow_id"],
                "run_key": item["run_key"],
                "version": item["version"],
                "status": item["status"],
                "current_step": item["current_step"],
                "next_step": item["next_step"],
                "updated_at": item["updated_at"],
            }
            for item in self.workflow.list_workflows(project_id)
        ]
        payload = {
            "states": sorted(state_refs, key=lambda item: (item["namespace"], item["key"])),
            "experiences": sorted(experience_refs, key=lambda item: item["id"]),
            "workflows": sorted(
                workflow_refs,
                key=lambda item: (item["workflow_id"], item["run_key"]),
            ),
        }
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return {
            "fingerprint": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
            "record_counts": {
                "states": len(state_refs),
                "experiences": len(experience_refs),
                "workflows": len(workflow_refs),
            },
            "has_authoritative_records": bool(
                state_refs or experience_refs or workflow_refs
            ),
        }

    @staticmethod
    def _checkpoint_metadata(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "kind": _CHECKPOINT_KIND,
            "captured_at": _now(),
            "continuity_fingerprint": summary["fingerprint"],
            "record_counts": summary["record_counts"],
            "has_authoritative_records": summary["has_authoritative_records"],
        }

    def start_session(self, project_id: str) -> dict[str, Any]:
        now = _now()
        session_id = str(uuid4())
        with self._connect(project_id) as connection:
            connection.execute(
                "INSERT INTO recovery_sessions(id, status, evidence_json, version, started_at, updated_at, closed_at) "
                "VALUES (?, ?, ?, 1, ?, ?, NULL)",
                (
                    session_id,
                    _SESSION_ACTIVE,
                    json.dumps({"kind": "session_started"}, separators=(",", ":")),
                    now,
                    now,
                ),
            )
        self.audit_database.add_repository_event(
            event_type="project_recovery.session_started",
            summary="Started private project recovery session",
            project_id=project_id,
            details={"session_id": session_id, "version": 1},
        )
        return {
            "project_id": project_id,
            "session_id": session_id,
            "recovery_version": 1,
            "status": "checkpoint_required",
        }

    def checkpoint(
        self,
        project_id: str,
        session_id: str,
        *,
        expected_version: int,
    ) -> dict[str, Any]:
        summary = self._continuity_metadata(project_id)
        now = _now()
        with self._connect(project_id) as connection:
            row = connection.execute(
                "SELECT * FROM recovery_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row is None:
                raise ProjectRecoveryConflict("Recovery session was not found")
            current = self._row_to_session(row)
            if current["status"] != _SESSION_ACTIVE:
                raise ProjectRecoveryConflict("Recovery session is no longer active")
            if current["version"] != expected_version:
                raise ProjectRecoveryConflict(
                    "Recovery session version mismatch: "
                    f"current={current['version']}, expected={expected_version}"
                )
            new_version = expected_version + 1
            evidence = self._checkpoint_metadata(summary)
            connection.execute(
                "UPDATE recovery_sessions SET evidence_json = ?, version = ?, updated_at = ? "
                "WHERE id = ?",
                (json.dumps(evidence, separators=(",", ":")), new_version, now, session_id),
            )
        self.audit_database.add_repository_event(
            event_type="project_recovery.checkpointed",
            summary="Checkpointed private project recovery metadata",
            project_id=project_id,
            details={
                "session_id": session_id,
                "version": new_version,
                "record_counts": summary["record_counts"],
            },
        )
        return {
            "project_id": project_id,
            "session_id": session_id,
            "recovery_version": new_version,
            "status": "checkpointed",
            "record_counts": summary["record_counts"],
        }

    def _classify(
        self,
        project_id: str,
        session: dict[str, Any],
    ) -> tuple[str, dict[str, Any] | None, bool]:
        evidence = session["evidence"]
        if evidence.get("kind") != _CHECKPOINT_KIND:
            return RECOVERY_POSSIBLY_INTERRUPTED, None, False
        summary = self._continuity_metadata(project_id)
        if not summary["has_authoritative_records"]:
            return RECOVERY_INSUFFICIENT_EVIDENCE, summary, False
        return (
            RECOVERY_AVAILABLE,
            summary,
            summary["fingerprint"] != evidence.get("continuity_fingerprint"),
        )

    def inspect(self, project_id: str) -> dict[str, Any]:
        session = self._latest_active_session(project_id)
        if session is None:
            return {
                "project_id": project_id,
                "status": RECOVERY_CLEAN,
                "recovery_available": False,
                "message": "No unfinished recovery session is recorded for this project.",
            }
        status, summary, changed = self._classify(project_id, session)
        payload: dict[str, Any] = {
            "project_id": project_id,
            "status": status,
            "session_id": session["id"],
            "recovery_version": session["version"],
            "recovery_available": status == RECOVERY_AVAILABLE,
            "state_changed_since_checkpoint": changed,
            "message": (
                "A persisted continuity checkpoint can be previewed before an explicit restore confirmation."
                if status == RECOVERY_AVAILABLE
                else "An active session alone is not treated as a crash; no state will be restored automatically."
            ),
        }
        if summary is not None:
            payload["record_counts"] = summary["record_counts"]
        return payload

    def preview(self, project_id: str, session_id: str) -> dict[str, Any]:
        session = self._get_session(project_id, session_id)
        if session is None:
            raise ProjectRecoveryConflict("Recovery session was not found")
        if session["status"] != _SESSION_ACTIVE:
            raise ProjectRecoveryConflict("Recovery session is no longer active")
        status, summary, changed = self._classify(project_id, session)
        if status != RECOVERY_AVAILABLE or summary is None:
            raise ProjectRecoveryConflict(
                f"Recovery preview is unavailable while status is {status}"
            )
        return {
            "project_id": project_id,
            "session_id": session_id,
            "recovery_version": session["version"],
            "status": status,
            "state_changed_since_checkpoint": changed,
            "record_counts": summary["record_counts"],
            "snapshot": self.handoff.build(project_id, mode="compact"),
        }

    def close_session(
        self,
        project_id: str,
        session_id: str,
        *,
        expected_version: int,
    ) -> dict[str, Any]:
        now = _now()
        with self._connect(project_id) as connection:
            row = connection.execute(
                "SELECT * FROM recovery_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row is None:
                raise ProjectRecoveryConflict("Recovery session was not found")
            current = self._row_to_session(row)
            if current["status"] != _SESSION_ACTIVE:
                raise ProjectRecoveryConflict("Recovery session is no longer active")
            if current["version"] != expected_version:
                raise ProjectRecoveryConflict(
                    "Recovery session version mismatch: "
                    f"current={current['version']}, expected={expected_version}"
                )
            new_version = expected_version + 1
            connection.execute(
                "UPDATE recovery_sessions SET status = ?, version = ?, updated_at = ?, closed_at = ? "
                "WHERE id = ?",
                (_SESSION_CLOSED, new_version, now, now, session_id),
            )
        self.audit_database.add_repository_event(
            event_type="project_recovery.session_closed",
            summary="Closed private project recovery session",
            project_id=project_id,
            details={"session_id": session_id, "version": new_version},
        )
        return {
            "project_id": project_id,
            "session_id": session_id,
            "recovery_version": new_version,
            "status": RECOVERY_CLEAN,
        }

    def confirm_restore(
        self,
        project_id: str,
        session_id: str,
        *,
        expected_version: int,
    ) -> dict[str, Any]:
        session = self._get_session(project_id, session_id)
        if session is None:
            raise ProjectRecoveryConflict("Recovery session was not found")
        if session["version"] != expected_version:
            raise ProjectRecoveryConflict(
                "Recovery session version mismatch: "
                f"current={session['version']}, expected={expected_version}"
            )
        if session["status"] != _SESSION_ACTIVE:
            raise ProjectRecoveryConflict("Recovery session is no longer active")
        status, _, changed = self._classify(project_id, session)
        if status != RECOVERY_AVAILABLE:
            raise ProjectRecoveryConflict(
                f"Recovery confirmation is unavailable while status is {status}"
            )
        now = _now()
        new_version = expected_version + 1
        with self._connect(project_id) as connection:
            updated = connection.execute(
                "UPDATE recovery_sessions SET status = ?, version = ?, updated_at = ?, closed_at = ? "
                "WHERE id = ? AND status = ? AND version = ?",
                (
                    _SESSION_RESTORED,
                    new_version,
                    now,
                    now,
                    session_id,
                    _SESSION_ACTIVE,
                    expected_version,
                ),
            )
            if updated.rowcount != 1:
                raise ProjectRecoveryConflict("Recovery session changed before confirmation")
        self.audit_database.add_repository_event(
            event_type="project_recovery.restored",
            summary="Confirmed project recovery from persisted state",
            project_id=project_id,
            details={
                "session_id": session_id,
                "version": new_version,
                "state_changed_since_checkpoint": changed,
            },
        )
        return {
            "project_id": project_id,
            "session_id": session_id,
            "recovery_version": new_version,
            "status": "restored",
            "resume_from": "authoritative_persisted_project_state",
            "state_changed_since_checkpoint": changed,
        }
