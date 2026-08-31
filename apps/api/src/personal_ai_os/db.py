from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from personal_ai_os_core import (
    Artifact,
    Conversation,
    ExecutionEvent,
    MemoryRecord,
    MemoryStatus,
    Message,
    MessageRole,
    RepositoryEvent,
    ProjectMetadata,
)
from personal_ai_os_mcp import ConnectionStatus, ConnectorDefinition


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
            project_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL, content TEXT NOT NULL, tool_refs_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS messages_conversation_created ON messages(conversation_id, created_at);
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY, type TEXT NOT NULL, text TEXT NOT NULL, source TEXT NOT NULL,
            confidence REAL NOT NULL, valid_from TEXT, status TEXT NOT NULL, project_id TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS memories_status_updated ON memories(status, updated_at DESC);
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, locator TEXT NOT NULL, title TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}', project_id TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS repository_events (
            id TEXT PRIMARY KEY, event_type TEXT NOT NULL, summary TEXT NOT NULL, artifact_id TEXT,
            project_id TEXT, details_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS repository_events_created ON repository_events(created_at DESC);
        CREATE TABLE IF NOT EXISTS execution_events (
            id TEXT PRIMARY KEY, conversation_id TEXT, type TEXT NOT NULL, status TEXT NOT NULL,
            tool TEXT, duration_ms INTEGER, payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        """,
    ),
    (
        2,
        """
        CREATE INDEX IF NOT EXISTS conversations_project_updated
            ON conversations(project_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS execution_events_conversation_created
            ON execution_events(conversation_id, created_at);
        """,
    ),
    (
        3,
        """
        CREATE TABLE IF NOT EXISTS mcp_connectors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            transport TEXT NOT NULL,
            endpoint TEXT,
            command TEXT,
            enabled INTEGER NOT NULL,
            allowed_tools_json TEXT NOT NULL DEFAULT '[]',
            connection_status TEXT NOT NULL,
            last_error TEXT,
            last_seen TEXT,
            timeout_seconds REAL NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS mcp_connectors_enabled_updated
            ON mcp_connectors(enabled, updated_at DESC);
        """,
    ),
    (
        4,
        """
        CREATE TABLE IF NOT EXISTS tenants (
            id TEXT PRIMARY KEY, deployment_mode TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS actors (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tenant_memberships (
            tenant_id TEXT NOT NULL REFERENCES tenants(id),
            actor_id TEXT NOT NULL REFERENCES actors(id),
            role TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, actor_id)
        );
        CREATE TABLE IF NOT EXISTS tenant_entitlements (
            tenant_id TEXT NOT NULL REFERENCES tenants(id),
            capability TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, capability)
        );
        CREATE TABLE IF NOT EXISTS tenant_settings (
            tenant_id TEXT NOT NULL REFERENCES tenants(id),
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, key)
        );
        ALTER TABLE conversations ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local';
        ALTER TABLE memories ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local';
        ALTER TABLE artifacts ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local';
        ALTER TABLE repository_events ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local';
        ALTER TABLE execution_events ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local';
        ALTER TABLE mcp_connectors ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local';
        CREATE INDEX IF NOT EXISTS conversations_tenant_updated
            ON conversations(tenant_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS memories_tenant_updated
            ON memories(tenant_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS artifacts_tenant_created
            ON artifacts(tenant_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS repository_events_tenant_created
            ON repository_events(tenant_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS execution_events_tenant_conversation
            ON execution_events(tenant_id, conversation_id, created_at);
        CREATE INDEX IF NOT EXISTS mcp_connectors_tenant_updated
            ON mcp_connectors(tenant_id, updated_at DESC);
        """,
    ),
    (
        5,
        """
        CREATE TABLE IF NOT EXISTS user_projects (
            tenant_id TEXT NOT NULL REFERENCES tenants(id),
            id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, id)
        );
        CREATE INDEX IF NOT EXISTS user_projects_tenant_created
            ON user_projects(tenant_id, created_at DESC);
        """,
    ),
    (
        6,
        """
        CREATE TABLE IF NOT EXISTS send_scope_receipts (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id),
            conversation_id TEXT,
            project_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            selected_files_json TEXT NOT NULL DEFAULT '[]',
            reviewed_memory_ids_json TEXT NOT NULL DEFAULT '[]',
            tool_availability_json TEXT NOT NULL DEFAULT '[]',
            context_categories_json TEXT NOT NULL DEFAULT '[]',
            approximate_context_tokens INTEGER NOT NULL,
            context_precision TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS send_scope_receipts_tenant_conversation
            ON send_scope_receipts(tenant_id, conversation_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS usage_ledger (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id),
            conversation_id TEXT,
            project_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            status TEXT NOT NULL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            token_precision TEXT NOT NULL,
            cost_usd REAL,
            cost_precision TEXT NOT NULL,
            latency_ms INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS usage_ledger_tenant_project_created
            ON usage_ledger(tenant_id, project_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS budget_policies (
            tenant_id TEXT NOT NULL REFERENCES tenants(id),
            scope_type TEXT NOT NULL,
            scope_id TEXT NOT NULL,
            period TEXT NOT NULL,
            limit_tokens INTEGER NOT NULL,
            warn_percent INTEGER NOT NULL,
            hard_limit INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, scope_type, scope_id, period)
        );
        CREATE TABLE IF NOT EXISTS tool_action_confirmations (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id),
            project_id TEXT NOT NULL,
            connector_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments_digest TEXT NOT NULL,
            preview_json TEXT NOT NULL,
            status TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            confirmed_at TEXT,
            consumed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS tool_action_confirmations_tenant_status
            ON tool_action_confirmations(tenant_id, status, expires_at);
        CREATE TABLE IF NOT EXISTS execution_runs (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id),
            conversation_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            status TEXT NOT NULL,
            retry_status TEXT NOT NULL,
            side_effect_status TEXT NOT NULL,
            detail_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS execution_runs_tenant_conversation
            ON execution_runs(tenant_id, conversation_id, created_at DESC);
        """,
    ),
    (
        7,
        """
        ALTER TABLE memories ADD COLUMN provenance_json TEXT NOT NULL DEFAULT '{}';
        ALTER TABLE memories ADD COLUMN source_reference TEXT;
        ALTER TABLE memories ADD COLUMN conflict_key TEXT;
        ALTER TABLE memories ADD COLUMN last_used_at TEXT;
        ALTER TABLE memories ADD COLUMN why_used TEXT;
        CREATE INDEX IF NOT EXISTS memories_tenant_conflict_key
            ON memories(tenant_id, conflict_key, status);
        """,
    ),
    (
        8,
        """
        ALTER TABLE tool_action_confirmations
            ADD COLUMN actor_id TEXT NOT NULL DEFAULT 'local-owner';
        CREATE INDEX IF NOT EXISTS tool_action_confirmations_actor_status
            ON tool_action_confirmations(tenant_id, actor_id, status, expires_at);
        CREATE TABLE IF NOT EXISTS budget_reservations (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES tenants(id),
            project_id TEXT NOT NULL,
            reserved_tokens INTEGER NOT NULL CHECK(reserved_tokens > 0),
            status TEXT NOT NULL CHECK(status IN ('active', 'committed', 'released', 'unknown')),
            reason TEXT NOT NULL,
            execution_id TEXT,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            settled_at TEXT
        );
        CREATE INDEX IF NOT EXISTS budget_reservations_tenant_project_status
            ON budget_reservations(tenant_id, project_id, status, expires_at);
        """,
    ),
]


class MigrationSafetyError(RuntimeError):
    """A migration was refused or rolled back before its schema receipt was committed."""


_MIGRATION_MARKERS: dict[int, tuple[str, ...]] = {
    6: (
        "send_scope_receipts",
        "usage_ledger",
        "budget_policies",
        "tool_action_confirmations",
        "execution_runs",
    ),
    7: (
        "memories.provenance_json",
        "memories.source_reference",
        "memories.conflict_key",
        "memories.last_used_at",
        "memories.why_used",
    ),
    8: (
        "tool_action_confirmations.actor_id",
        "budget_reservations",
    ),
}


def _statements(script: str) -> list[str]:
    """Split the repository's migration SQL without using executescript's implicit commit."""
    statements: list[str] = []
    buffer = ""
    for line in script.splitlines():
        buffer += line + "\n"
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                statements.append(statement)
            buffer = ""
    if buffer.strip():
        raise MigrationSafetyError("Migration SQL contains an incomplete statement")
    return statements


class Database:
    def __init__(
        self,
        path: Path,
        *,
        tenant_id: str = "local",
        actor_id: str = "local-owner",
        deployment_mode: str = "community",
        migration_failure_hook: Callable[[int, str], None] | None = None,
        sqlite_timeout_seconds: float = 10,
    ) -> None:
        self.path = path
        self.tenant_id = tenant_id
        self.actor_id = actor_id
        self.deployment_mode = deployment_mode
        self._migration_failure_hook = migration_failure_hook
        self._sqlite_timeout_seconds = sqlite_timeout_seconds

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=self._sqlite_timeout_seconds)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _marker_exists(self, connection: sqlite3.Connection, marker: str) -> bool:
        if "." not in marker:
            return bool(
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (marker,)
                ).fetchone()
            )
        table, column = marker.split(".", maxsplit=1)
        columns = connection.execute(f"PRAGMA table_info({table})").fetchall()
        return any(row["name"] == column for row in columns)

    def _assert_no_partial_migration(self, connection: sqlite3.Connection, applied: set[int]) -> None:
        for version, markers in _MIGRATION_MARKERS.items():
            present = [self._marker_exists(connection, marker) for marker in markers]
            if any(present) and version not in applied:
                raise MigrationSafetyError(
                    f"Refusing to continue: migration v{version} has schema changes without its committed receipt. "
                    "Restore the backup created before the interrupted migration."
                )
            if version in applied and not all(present):
                raise MigrationSafetyError(
                    f"Refusing to continue: migration v{version} is recorded but its schema markers are incomplete."
                )

    def _checkpoint(self, version: int, phase: str) -> None:
        if self._migration_failure_hook is not None:
            self._migration_failure_hook(version, phase)

    def migrate(self) -> None:
        existed_before = self.path.exists() and self.path.stat().st_size > 0
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {row["version"] for row in connection.execute("SELECT version FROM schema_migrations")}
            self._assert_no_partial_migration(connection, applied)
        pending = [(version, sql) for version, sql in MIGRATIONS if version not in applied]
        if existed_before and pending:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_path = self.path.with_name(
                f"{self.path.name}.backup-before-v{pending[0][0]}-{timestamp}"
            )
            with sqlite3.connect(self.path) as source, sqlite3.connect(backup_path) as target:
                source.backup(target)
        try:
            with self.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                for version, sql in pending:
                    self._checkpoint(version, "before_schema")
                    for statement in _statements(sql):
                        connection.execute(statement)
                        self._checkpoint(version, "after_statement")
                    self._checkpoint(version, "before_receipt")
                    connection.execute(
                        "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)", (version, _now())
                    )
                    self._checkpoint(version, "after_receipt")
                now = _now()
                connection.execute(
                    "INSERT OR IGNORE INTO tenants(id, deployment_mode, created_at) VALUES (?, ?, ?)",
                    (self.tenant_id, self.deployment_mode, now),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO actors(id, created_at) VALUES (?, ?)",
                    (self.actor_id, now),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO tenant_memberships(tenant_id, actor_id, role, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (self.tenant_id, self.actor_id, "owner", now),
                )
                if self.tenant_id == "local":
                    connection.execute(
                        "INSERT OR IGNORE INTO tenant_settings(tenant_id, key, value, updated_at) "
                        "SELECT 'local', key, value, updated_at FROM app_settings"
                    )
        except MigrationSafetyError:
            raise
        except Exception as exc:
            raise MigrationSafetyError(
                "Migration failed before commit; the workspace schema was rolled back and the pre-migration backup is retained."
            ) from exc

    def create_conversation(self, provider: str, model: str, project_id: str | None, title: str) -> Conversation:
        record = Conversation(
            id=str(uuid4()), title=title[:120], provider=provider, model=model, project_id=project_id
        )
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO conversations(id, title, provider, model, project_id, created_at, updated_at, tenant_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.title,
                    record.provider,
                    record.model,
                    record.project_id,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                    self.tenant_id,
                ),
            )
        return record

    def create_user_project(self, metadata: ProjectMetadata) -> ProjectMetadata:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO user_projects(tenant_id, id, name, description, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    self.tenant_id,
                    metadata.id,
                    metadata.name,
                    metadata.description,
                    _now(),
                ),
            )
        return metadata

    def list_user_projects(self) -> list[ProjectMetadata]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, description FROM user_projects WHERE tenant_id = ? ORDER BY created_at ASC, id ASC",
                (self.tenant_id,),
            ).fetchall()
        return [
            ProjectMetadata(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                icon="folder",
            )
            for row in rows
        ]

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM conversations WHERE id = ? AND tenant_id = ?",
                (conversation_id, self.tenant_id),
            ).fetchone()
        return Conversation(**dict(row)) if row else None

    def list_conversations(self, project_id: str | None = None) -> list[Conversation]:
        query = "SELECT * FROM conversations WHERE tenant_id = ?"
        params: tuple[Any, ...] = (self.tenant_id,)
        if project_id:
            query += " AND project_id = ?"
            params = (self.tenant_id, project_id)
        query += " ORDER BY updated_at DESC"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Conversation(**dict(row)) for row in rows]

    def update_conversation_title(self, conversation_id: str, title: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND tenant_id = ?",
                (title[:120], _now(), conversation_id, self.tenant_id),
            )

    def update_conversation_route(self, conversation_id: str, provider: str, model: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE conversations SET provider = ?, model = ?, updated_at = ? "
                "WHERE id = ? AND tenant_id = ?",
                (provider, model, _now(), conversation_id, self.tenant_id),
            )

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        tool_refs: list[str] | None = None,
    ) -> Message:
        if self.get_conversation(conversation_id) is None:
            raise KeyError("Conversation not found in current tenant")
        record = Message(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_refs=tool_refs or [],
        )
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.conversation_id,
                    record.role.value,
                    record.content,
                    json.dumps(record.tool_refs),
                    record.created_at.isoformat(),
                ),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ? AND tenant_id = ?",
                (_now(), conversation_id, self.tenant_id),
            )
        return record

    def list_messages(self, conversation_id: str) -> list[Message]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT messages.* FROM messages JOIN conversations "
                "ON conversations.id = messages.conversation_id "
                "WHERE messages.conversation_id = ? AND conversations.tenant_id = ? "
                "ORDER BY messages.created_at",
                (conversation_id, self.tenant_id),
            ).fetchall()
        return [
            Message(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],
                content=row["content"],
                tool_refs=json.loads(row["tool_refs_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def create_memory(self, values: dict[str, Any]) -> MemoryRecord:
        now = _now()
        values = dict(values)
        if not values.get("provenance"):
            values["provenance"] = {"source": values.get("source", "user")}
        if not values.get("conflict_key"):
            values["conflict_key"] = self._memory_conflict_key(values)
        if values.get("conflict_key"):
            with self.connect() as connection:
                conflict = connection.execute(
                    "SELECT id FROM memories WHERE tenant_id = ? AND type = ? AND project_id IS ? AND conflict_key = ? "
                    "AND status = ? AND text != ? LIMIT 1",
                    (
                        self.tenant_id,
                        values["type"],
                        values.get("project_id"),
                        values["conflict_key"],
                        MemoryStatus.ACTIVE.value,
                        values["text"],
                    ),
                ).fetchone()
            if conflict:
                values["status"] = MemoryStatus.CONFLICT_REVIEW_REQUIRED
        record = MemoryRecord(id=str(uuid4()), created_at=now, updated_at=now, **values)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO memories(id, type, text, source, confidence, valid_from, status, "
                "project_id, created_at, updated_at, tenant_id, provenance_json, source_reference, conflict_key, last_used_at, why_used) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.type,
                    record.text,
                    record.source,
                    record.confidence,
                    record.valid_from.isoformat() if record.valid_from else None,
                    record.status.value,
                    record.project_id,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                    self.tenant_id,
                    json.dumps(record.provenance),
                    record.source_reference,
                    record.conflict_key,
                    record.last_used_at.isoformat() if record.last_used_at else None,
                    record.why_used,
                ),
            )
        return record

    @staticmethod
    def _memory_conflict_key(values: dict[str, Any]) -> str | None:
        explicit = values.get("conflict_key")
        if explicit:
            return str(explicit)[:160]
        text = " ".join(str(values.get("text", "")).lower().split())
        for delimiter in ("=", ":", " is ", " are "):
            if delimiter in text:
                subject = text.split(delimiter, 1)[0].strip()
                if subject:
                    return subject[:160]
        return None

    def list_memories(self, status: str | None = None) -> list[MemoryRecord]:
        query = "SELECT * FROM memories WHERE tenant_id = ?"
        params: tuple[Any, ...] = (self.tenant_id,)
        if status:
            query += " AND status = ?"
            params = (self.tenant_id, status)
        query += " ORDER BY updated_at DESC"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._memory_from_row(row) for row in rows]

    @staticmethod
    def _memory_from_row(row: sqlite3.Row) -> MemoryRecord:
        values = dict(row)
        provenance = values.pop("provenance_json", "{}")
        values["provenance"] = json.loads(provenance)
        return MemoryRecord(**values)

    def update_memory(self, memory_id: str, values: dict[str, Any]) -> MemoryRecord | None:
        allowed = {
            "type", "text", "source", "confidence", "valid_from", "status", "project_id",
            "provenance", "source_reference", "conflict_key", "last_used_at", "why_used",
        }
        updates = {key: value for key, value in values.items() if key in allowed}
        if not updates:
            return self.get_memory(memory_id)
        current = self.get_memory(memory_id)
        if current is None:
            return None
        if updates.get("status") == MemoryStatus.ACTIVE or getattr(updates.get("status"), "value", None) == MemoryStatus.ACTIVE.value:
            candidate = current.model_dump()
            candidate.update(updates)
            conflict_key = self._memory_conflict_key(candidate)
            if conflict_key:
                with self.connect() as connection:
                    conflict = connection.execute(
                        "SELECT id FROM memories WHERE tenant_id = ? AND type = ? AND project_id IS ? AND conflict_key = ? "
                        "AND status = ? AND id != ? LIMIT 1",
                        (
                            self.tenant_id,
                            candidate["type"],
                            candidate.get("project_id"),
                            conflict_key,
                            MemoryStatus.ACTIVE.value,
                            memory_id,
                        ),
                    ).fetchone()
                if conflict:
                    updates["status"] = MemoryStatus.CONFLICT_REVIEW_REQUIRED
        normalized = {
            key: (
                value.value if hasattr(value, "value") else value.isoformat() if isinstance(value, datetime)
                else json.dumps(value) if key == "provenance" else value
            )
            for key, value in updates.items()
        }
        normalized["updated_at"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in normalized)
        with self.connect() as connection:
            cursor = connection.execute(
                f"UPDATE memories SET {assignments} WHERE id = ? AND tenant_id = ?",
                (*normalized.values(), memory_id, self.tenant_id),
            )
        return self.get_memory(memory_id) if cursor.rowcount else None

    def list_memory_conflicts(self, memory_id: str) -> list[MemoryRecord]:
        current = self.get_memory(memory_id)
        if current is None or not current.conflict_key:
            return []
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM memories WHERE tenant_id = ? AND type = ? AND project_id IS ? AND conflict_key = ? "
                "AND id != ? AND status IN (?, ?) ORDER BY updated_at DESC",
                (
                    self.tenant_id,
                    current.type,
                    current.project_id,
                    current.conflict_key,
                    memory_id,
                    MemoryStatus.ACTIVE.value,
                    MemoryStatus.CONFLICT_REVIEW_REQUIRED.value,
                ),
            ).fetchall()
        return [self._memory_from_row(row) for row in rows]

    def resolve_memory_conflict(
        self,
        memory_id: str,
        *,
        action: str,
        scope_project_id: str | None = None,
    ) -> MemoryRecord | None:
        current = self.get_memory(memory_id)
        if current is None:
            return None
        if action == "keep_existing":
            return self.update_memory(memory_id, {"status": MemoryStatus.REJECTED})
        if action == "keep_both":
            if not scope_project_id:
                raise ValueError("Keeping both conflicting memories requires an explicit project scope")
            scoped = current.model_copy(update={"project_id": scope_project_id})
            if scoped.conflict_key:
                with self.connect() as connection:
                    conflict = connection.execute(
                        "SELECT 1 FROM memories WHERE tenant_id = ? AND type = ? AND project_id IS ? AND conflict_key = ? "
                        "AND status = ? AND id != ? LIMIT 1",
                        (
                            self.tenant_id,
                            scoped.type,
                            scope_project_id,
                            scoped.conflict_key,
                            MemoryStatus.ACTIVE.value,
                            memory_id,
                        ),
                    ).fetchone()
                if conflict:
                    raise ValueError("That project scope still has an active conflicting memory")
            return self.update_memory(memory_id, {"project_id": scope_project_id, "status": MemoryStatus.ACTIVE})
        if action not in {"replace", "merge"}:
            raise ValueError("Unsupported memory conflict resolution")
        with self.connect() as connection:
            connection.execute(
                "UPDATE memories SET status = ?, updated_at = ? WHERE tenant_id = ? AND type = ? AND project_id IS ? "
                "AND conflict_key = ? AND status = ? AND id != ?",
                (
                    MemoryStatus.SUPERSEDED.value,
                    _now(),
                    self.tenant_id,
                    current.type,
                    current.project_id,
                    current.conflict_key,
                    MemoryStatus.ACTIVE.value,
                    memory_id,
                ),
            )
        return self.update_memory(memory_id, {"status": MemoryStatus.ACTIVE})

    def mark_memories_used(self, memory_ids: list[str], *, why_used: str) -> None:
        if not memory_ids:
            return
        placeholders = ", ".join("?" for _ in memory_ids)
        with self.connect() as connection:
            connection.execute(
                f"UPDATE memories SET last_used_at = ?, why_used = ? WHERE tenant_id = ? AND id IN ({placeholders})",
                (_now(), why_used, self.tenant_id, *memory_ids),
            )

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM memories WHERE id = ? AND tenant_id = ?",
                (memory_id, self.tenant_id),
            ).fetchone()
        return self._memory_from_row(row) if row else None

    def create_artifact(self, values: dict[str, Any]) -> Artifact:
        record = Artifact(id=str(uuid4()), **values)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO artifacts(id, kind, locator, title, metadata_json, project_id, created_at, tenant_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.kind,
                    record.locator,
                    record.title,
                    json.dumps(record.metadata),
                    record.project_id,
                    record.created_at.isoformat(),
                    self.tenant_id,
                ),
            )
        self.add_repository_event(
            event_type="artifact.created",
            summary=f"Created artifact: {record.title}",
            artifact_id=record.id,
            project_id=record.project_id,
            details={"kind": record.kind},
        )
        return record

    def list_artifacts(self) -> list[Artifact]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM artifacts WHERE tenant_id = ? ORDER BY created_at DESC",
                (self.tenant_id,),
            ).fetchall()
        return [
            Artifact(
                id=row["id"],
                kind=row["kind"],
                locator=row["locator"],
                title=row["title"],
                metadata=json.loads(row["metadata_json"]),
                project_id=row["project_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def add_repository_event(
        self,
        event_type: str,
        summary: str,
        artifact_id: str | None = None,
        project_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> RepositoryEvent:
        record = RepositoryEvent(
            id=str(uuid4()),
            event_type=event_type,
            summary=summary,
            artifact_id=artifact_id,
            project_id=project_id,
            details=details or {},
        )
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO repository_events(id, event_type, summary, artifact_id, project_id, "
                "details_json, created_at, tenant_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.event_type,
                    record.summary,
                    record.artifact_id,
                    record.project_id,
                    json.dumps(record.details),
                    record.created_at.isoformat(),
                    self.tenant_id,
                ),
            )
        return record

    def list_repository_events(self) -> list[RepositoryEvent]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM repository_events WHERE tenant_id = ? ORDER BY created_at DESC",
                (self.tenant_id,),
            ).fetchall()
        return [
            RepositoryEvent(
                id=row["id"],
                event_type=row["event_type"],
                summary=row["summary"],
                artifact_id=row["artifact_id"],
                project_id=row["project_id"],
                details=json.loads(row["details_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def add_execution_event(self, event: dict[str, Any]) -> None:
        conversation_id = event.get("conversation_id")
        if conversation_id and self.get_conversation(conversation_id) is None:
            raise KeyError("Conversation not found in current tenant")
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO execution_events(id, conversation_id, type, status, tool, duration_ms, "
                "payload_json, created_at, tenant_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event["id"],
                    conversation_id,
                    event["type"],
                    event["status"],
                    event.get("tool"),
                    event.get("duration_ms"),
                    json.dumps(event.get("payload", {})),
                    event["created_at"],
                    self.tenant_id,
                ),
            )

    def list_execution_events(self, conversation_id: str) -> list[ExecutionEvent]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM execution_events WHERE conversation_id = ? AND tenant_id = ? "
                "ORDER BY created_at, rowid",
                (conversation_id, self.tenant_id),
            ).fetchall()
        return [
            ExecutionEvent(
                id=row["id"],
                conversation_id=row["conversation_id"],
                type=row["type"],
                status=row["status"],
                tool=row["tool"],
                duration_ms=row["duration_ms"],
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_setting(self, key: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM tenant_settings WHERE tenant_id = ? AND key = ?",
                (self.tenant_id, key),
            ).fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO tenant_settings(tenant_id, key, value, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(tenant_id, key) DO UPDATE SET "
                "value = excluded.value, updated_at = excluded.updated_at",
                (self.tenant_id, key, value, _now()),
            )

    def sync_entitlements(self, values: dict[str, bool]) -> None:
        now = _now()
        with self.connect() as connection:
            for capability, enabled in values.items():
                connection.execute(
                    "INSERT INTO tenant_entitlements(tenant_id, capability, enabled, updated_at) "
                    "VALUES (?, ?, ?, ?) ON CONFLICT(tenant_id, capability) DO UPDATE SET "
                    "enabled = excluded.enabled, updated_at = excluded.updated_at",
                    (self.tenant_id, capability, int(enabled), now),
                )

    @staticmethod
    def _connector_from_row(row: sqlite3.Row) -> ConnectorDefinition:
        return ConnectorDefinition(
            id=row["id"],
            name=row["name"],
            transport=row["transport"],
            endpoint=row["endpoint"],
            command=row["command"],
            enabled=bool(row["enabled"]),
            allowed_tools=json.loads(row["allowed_tools_json"]),
            connection_status=row["connection_status"],
            last_error=row["last_error"],
            last_seen=row["last_seen"],
            timeout_seconds=row["timeout_seconds"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_mcp_connector(self, values: dict[str, Any]) -> ConnectorDefinition:
        now = _now()
        enabled = bool(values.get("enabled", True))
        record = ConnectorDefinition(
            id=str(uuid4()),
            connection_status=(
                ConnectionStatus.CONFIGURED if enabled else ConnectionStatus.DISABLED
            ),
            created_at=now,
            updated_at=now,
            **values,
        )
        self.save_mcp_connector(record, insert=True)
        return record

    def save_mcp_connector(
        self, connector: ConnectorDefinition, *, insert: bool = False
    ) -> None:
        values = (
            connector.id,
            connector.name,
            connector.transport.value,
            connector.endpoint,
            connector.command,
            int(connector.enabled),
            json.dumps(connector.allowed_tools),
            connector.connection_status.value,
            connector.last_error,
            connector.last_seen.isoformat() if connector.last_seen else None,
            connector.timeout_seconds,
            connector.created_at.isoformat(),
            connector.updated_at.isoformat(),
        )
        with self.connect() as connection:
            if insert:
                connection.execute(
                    "INSERT INTO mcp_connectors(id, name, transport, endpoint, command, enabled, "
                    "allowed_tools_json, connection_status, last_error, last_seen, timeout_seconds, "
                    "created_at, updated_at, tenant_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (*values, self.tenant_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE mcp_connectors SET
                        name = ?, transport = ?, endpoint = ?, command = ?, enabled = ?,
                        allowed_tools_json = ?, connection_status = ?, last_error = ?,
                        last_seen = ?, timeout_seconds = ?, created_at = ?, updated_at = ?
                    WHERE id = ? AND tenant_id = ?
                    """,
                    (*values[1:], connector.id, self.tenant_id),
                )

    def get_mcp_connector(self, connector_id: str) -> ConnectorDefinition | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM mcp_connectors WHERE id = ? AND tenant_id = ?",
                (connector_id, self.tenant_id),
            ).fetchone()
        return self._connector_from_row(row) if row else None

    def list_mcp_connectors(self) -> list[ConnectorDefinition]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM mcp_connectors WHERE tenant_id = ? ORDER BY updated_at DESC",
                (self.tenant_id,),
            ).fetchall()
        return [self._connector_from_row(row) for row in rows]
