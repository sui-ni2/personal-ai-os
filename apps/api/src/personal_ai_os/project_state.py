from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from personal_ai_os_core import ProjectStateStatus

from .db import Database


MAX_CONTEXT_RECORDS = 80
MAX_CONTEXT_CHARS = 40_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_project_id(project_id: str) -> str:
    if (
        not project_id
        or project_id in {".", ".."}
        or any(
            ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
            for ch in project_id
        )
    ):
        raise ValueError("project_id contains unsupported path characters")
    return project_id


def _tenant_scope(tenant_id: str) -> str:
    return hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()[:16]


def _project_storage_key(project_id: str) -> str:
    """Return a 128-bit opaque on-disk key for a validated project identifier.

    Keeping the key compact avoids exceeding the Windows legacy path limit in deep data roots
    while retaining a collision space far beyond the supported project-registry cardinality.
    """
    digest = hashlib.sha256(project_id.encode("utf-8")).digest()[:16]
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


class ProjectStateConflict(RuntimeError):
    pass


@dataclass(frozen=True)
class ProjectStateSnapshot:
    project_id: str
    states: list[dict[str, Any]]
    experiences: list[dict[str, Any]]
    truncated: bool = False

    def as_context(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "states": self.states,
            "experiences": self.experiences,
            "truncated": self.truncated,
        }


class ProjectStateService:
    """Private, project-scoped continuity state with physical project isolation.

    Public source code defines the protocol only. Runtime values are stored in a separate SQLite
    database for each project under ``data/private/p``. The main repository database is
    used only for audit events, so project state does not leak into the generic Memory listing.
    """

    def __init__(
        self,
        audit_database: Database,
        *,
        data_dir: Path | None = None,
        tenant_id: str | None = None,
    ) -> None:
        self.audit_database = audit_database
        self.data_dir = Path(data_dir) if data_dir is not None else audit_database.path.parent
        self.tenant_id = tenant_id or audit_database.tenant_id

    def storage_path(self, project_id: str) -> Path:
        project = _safe_project_id(project_id)
        return self._storage_root() / _project_storage_key(project) / "s.db"

    def _storage_root(self) -> Path:
        # Keep the fixed segments compact: SQLite also creates journal/WAL files beside the database,
        # and deep Windows data roots otherwise exceed the legacy path-length limit.
        return self.data_dir / "private" / "p" / _tenant_scope(self.tenant_id)

    def _legacy_storage_root(self) -> Path:
        return self.data_dir / "private" / "project-state" / _tenant_scope(self.tenant_id)

    def _legacy_storage_path(self, project_id: str) -> Path | None:
        """Find a pre-v0.4 private database without constructing a path from user input.

        Older releases used the project identifier as a directory name.  We inspect only direct
        children of the fixed tenant root, resolve each candidate, and reject a symlink that
        escapes that root.  The identifier is used solely as a filename comparison.
        """
        root = self._legacy_storage_root()
        if not root.is_dir():
            return None
        resolved_root = root.resolve()
        for candidate in root.iterdir():
            if candidate.name != project_id or not candidate.is_dir():
                continue
            resolved_candidate = candidate.resolve()
            if resolved_candidate.parent != resolved_root:
                return None
            database = resolved_candidate / "state.sqlite3"
            if not database.is_file():
                return None
            resolved_database = database.resolve()
            if resolved_database.parent != resolved_candidate:
                return None
            return resolved_database
        return None

    @staticmethod
    def _copy_database_once(source: Path, target: Path) -> None:
        """Copy a legacy SQLite database atomically, preserving the original as a rollback source."""
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix="m-", suffix="", dir=target.parent
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            source_connection = sqlite3.connect(source)
            target_connection = sqlite3.connect(temporary)
            try:
                source_connection.backup(target_connection)
            finally:
                # sqlite3.Connection's context manager commits but does not close.  Close both
                # handles before publishing and unlinking on Windows.
                target_connection.close()
                source_connection.close()
            try:
                # A hard link is an atomic no-overwrite publish on the same volume.  A concurrent
                # initializer that won the race keeps its database; both copies have the same source.
                os.link(temporary, target)
            except FileExistsError:
                return
        finally:
            temporary.unlink(missing_ok=True)

    def _preserve_legacy_storage(self, project_id: str, target: Path) -> None:
        if target.exists():
            return
        legacy = self._legacy_storage_path(project_id)
        if legacy is not None:
            self._copy_database_once(legacy, target)

    @contextmanager
    def _connect(self, project_id: str) -> Iterator[sqlite3.Connection]:
        project = _safe_project_id(project_id)
        path = self.storage_path(project)
        self._preserve_legacy_storage(project, path)
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
            CREATE TABLE IF NOT EXISTS current_state (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value_json TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence REAL NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (namespace, key)
            );
            CREATE TABLE IF NOT EXISTS state_history (
                id TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value_json TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence REAL NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS state_history_lookup
                ON state_history(namespace, key, version DESC);
            CREATE TABLE IF NOT EXISTS experiences (
                id TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS experiences_created
                ON experiences(created_at DESC);
            """
        )

    @staticmethod
    def _state_from_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "namespace": row["namespace"],
            "key": row["key"],
            "value": json.loads(row["value_json"]),
            "source": row["source"],
            "confidence": row["confidence"],
            "version": row["version"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_state(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect(project_id) as connection:
            rows = connection.execute(
                "SELECT * FROM current_state ORDER BY namespace, key"
            ).fetchall()
        return [self._state_from_row(row) for row in rows]

    def put_state(
        self,
        *,
        project_id: str,
        namespace: str,
        key: str,
        value: dict[str, Any],
        source: str,
        confidence: float = 1.0,
        lock: bool = False,
        expected_version: int | None = None,
        supersede_locked: bool = False,
    ) -> dict[str, Any]:
        now = _now()
        value_json = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        with self._connect(project_id) as connection:
            current = connection.execute(
                "SELECT * FROM current_state WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()

            if current is None:
                if expected_version not in {None, 0}:
                    raise ProjectStateConflict(
                        f"State {namespace}/{key} does not exist; expected_version must be 0"
                    )
                version = 1
                created_at = now
            else:
                current_version = int(current["version"])
                if expected_version is not None and expected_version != current_version:
                    raise ProjectStateConflict(
                        f"State {namespace}/{key} version mismatch: current={current_version}, expected={expected_version}"
                    )
                if current["status"] == ProjectStateStatus.LOCKED.value and not supersede_locked:
                    raise ProjectStateConflict(
                        f"State {namespace}/{key} is locked; explicit supersede_locked=true is required"
                    )
                connection.execute(
                    "INSERT INTO state_history(id, namespace, key, value_json, source, confidence, version, status, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid4()),
                        current["namespace"],
                        current["key"],
                        current["value_json"],
                        current["source"],
                        current["confidence"],
                        current_version,
                        current["status"],
                        now,
                    ),
                )
                version = current_version + 1
                created_at = current["created_at"]

            status = ProjectStateStatus.LOCKED.value if lock else ProjectStateStatus.ACTIVE.value
            connection.execute(
                "INSERT INTO current_state(namespace, key, value_json, source, confidence, version, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(namespace, key) DO UPDATE SET "
                "value_json = excluded.value_json, source = excluded.source, confidence = excluded.confidence, "
                "version = excluded.version, status = excluded.status, updated_at = excluded.updated_at",
                (
                    namespace,
                    key,
                    value_json,
                    source,
                    confidence,
                    version,
                    status,
                    created_at,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM current_state WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()
            assert row is not None
            result = self._state_from_row(row)

        self.audit_database.add_repository_event(
            event_type="project_state.updated",
            summary=f"Updated private project state {namespace}/{key}",
            project_id=project_id,
            details={
                "namespace": namespace,
                "key": key,
                "version": result["version"],
                "status": result["status"],
            },
        )
        return {"project_id": project_id, **result}

    def list_history(
        self,
        project_id: str,
        *,
        namespace: str | None = None,
        key: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM state_history WHERE 1 = 1"
        params: list[Any] = []
        if namespace is not None:
            query += " AND namespace = ?"
            params.append(namespace)
        if key is not None:
            query += " AND key = ?"
            params.append(key)
        query += " ORDER BY created_at DESC, version DESC"
        with self._connect(project_id) as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [
            {
                "id": row["id"],
                "namespace": row["namespace"],
                "key": row["key"],
                "value": json.loads(row["value_json"]),
                "source": row["source"],
                "confidence": row["confidence"],
                "version": row["version"],
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def append_experience(
        self,
        *,
        project_id: str,
        namespace: str,
        text: str,
        source: str,
        confidence: float,
    ) -> dict[str, Any]:
        item = {
            "id": str(uuid4()),
            "namespace": namespace,
            "text": text,
            "source": source,
            "confidence": confidence,
            "created_at": _now(),
        }
        with self._connect(project_id) as connection:
            connection.execute(
                "INSERT INTO experiences(id, namespace, text, source, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    item["id"],
                    item["namespace"],
                    item["text"],
                    item["source"],
                    item["confidence"],
                    item["created_at"],
                ),
            )
        self.audit_database.add_repository_event(
            event_type="project_experience.appended",
            summary=f"Appended private project experience in {namespace}",
            project_id=project_id,
            details={"namespace": namespace, "experience_id": item["id"]},
        )
        return {"project_id": project_id, **item}

    def list_experience(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect(project_id) as connection:
            rows = connection.execute(
                "SELECT * FROM experiences ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def snapshot(self, project_id: str) -> ProjectStateSnapshot:
        return ProjectStateSnapshot(
            project_id=project_id,
            states=self.list_state(project_id)[:MAX_CONTEXT_RECORDS],
            experiences=self.list_experience(project_id)[:MAX_CONTEXT_RECORDS],
        )

    def context_json(self, project_id: str) -> str:
        payload = self.snapshot(project_id).as_context()
        encoded = json.dumps(payload, ensure_ascii=False)
        if len(encoded) <= MAX_CONTEXT_CHARS:
            return encoded

        payload["truncated"] = True
        while payload["experiences"] and len(json.dumps(payload, ensure_ascii=False)) > MAX_CONTEXT_CHARS:
            payload["experiences"].pop()
        while payload["states"] and len(json.dumps(payload, ensure_ascii=False)) > MAX_CONTEXT_CHARS:
            payload["states"].pop()
        encoded = json.dumps(payload, ensure_ascii=False)
        if len(encoded) > MAX_CONTEXT_CHARS:
            payload = {
                "project_id": project_id,
                "states": [],
                "experiences": [],
                "truncated": True,
            }
            encoded = json.dumps(payload, ensure_ascii=False)
        return encoded
