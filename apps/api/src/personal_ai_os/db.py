from __future__ import annotations

import json
import sqlite3
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
    Message,
    MessageRole,
    RepositoryEvent,
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
]


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def migrate(self) -> None:
        existed_before = self.path.exists() and self.path.stat().st_size > 0
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {row["version"] for row in connection.execute("SELECT version FROM schema_migrations")}
        pending = [(version, sql) for version, sql in MIGRATIONS if version not in applied]
        if existed_before and applied and pending:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_path = self.path.with_name(
                f"{self.path.name}.backup-before-v{pending[0][0]}-{timestamp}"
            )
            with sqlite3.connect(self.path) as source, sqlite3.connect(backup_path) as target:
                source.backup(target)
        with self.connect() as connection:
            for version, sql in pending:
                connection.executescript(sql)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)", (version, _now())
                )

    def create_conversation(self, provider: str, model: str, project_id: str | None, title: str) -> Conversation:
        record = Conversation(
            id=str(uuid4()), title=title[:120], provider=provider, model=model, project_id=project_id
        )
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.title,
                    record.provider,
                    record.model,
                    record.project_id,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
        return record

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        return Conversation(**dict(row)) if row else None

    def list_conversations(self, project_id: str | None = None) -> list[Conversation]:
        query = "SELECT * FROM conversations"
        params: tuple[Any, ...] = ()
        if project_id:
            query += " WHERE project_id = ?"
            params = (project_id,)
        query += " ORDER BY updated_at DESC"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Conversation(**dict(row)) for row in rows]

    def update_conversation_title(self, conversation_id: str, title: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title[:120], _now(), conversation_id),
            )

    def update_conversation_route(self, conversation_id: str, provider: str, model: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE conversations SET provider = ?, model = ?, updated_at = ? WHERE id = ?",
                (provider, model, _now(), conversation_id),
            )

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        tool_refs: list[str] | None = None,
    ) -> Message:
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
                "UPDATE conversations SET updated_at = ? WHERE id = ?", (_now(), conversation_id)
            )
        return record

    def list_messages(self, conversation_id: str) -> list[Message]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at", (conversation_id,)
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
        record = MemoryRecord(id=str(uuid4()), created_at=now, updated_at=now, **values)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                ),
            )
        return record

    def list_memories(self, status: str | None = None) -> list[MemoryRecord]:
        query = "SELECT * FROM memories"
        params: tuple[Any, ...] = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY updated_at DESC"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [MemoryRecord(**dict(row)) for row in rows]

    def update_memory(self, memory_id: str, values: dict[str, Any]) -> MemoryRecord | None:
        allowed = {"type", "text", "source", "confidence", "valid_from", "status", "project_id"}
        updates = {key: value for key, value in values.items() if key in allowed}
        if not updates:
            return self.get_memory(memory_id)
        normalized = {
            key: (value.value if hasattr(value, "value") else value.isoformat() if isinstance(value, datetime) else value)
            for key, value in updates.items()
        }
        normalized["updated_at"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in normalized)
        with self.connect() as connection:
            cursor = connection.execute(
                f"UPDATE memories SET {assignments} WHERE id = ?", (*normalized.values(), memory_id)
            )
        return self.get_memory(memory_id) if cursor.rowcount else None

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return MemoryRecord(**dict(row)) if row else None

    def create_artifact(self, values: dict[str, Any]) -> Artifact:
        record = Artifact(id=str(uuid4()), **values)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.kind,
                    record.locator,
                    record.title,
                    json.dumps(record.metadata),
                    record.project_id,
                    record.created_at.isoformat(),
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
            rows = connection.execute("SELECT * FROM artifacts ORDER BY created_at DESC").fetchall()
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
                "INSERT INTO repository_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.event_type,
                    record.summary,
                    record.artifact_id,
                    record.project_id,
                    json.dumps(record.details),
                    record.created_at.isoformat(),
                ),
            )
        return record

    def list_repository_events(self) -> list[RepositoryEvent]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM repository_events ORDER BY created_at DESC").fetchall()
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
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO execution_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event["id"],
                    event.get("conversation_id"),
                    event["type"],
                    event["status"],
                    event.get("tool"),
                    event.get("duration_ms"),
                    json.dumps(event.get("payload", {})),
                    event["created_at"],
                ),
            )

    def list_execution_events(self, conversation_id: str) -> list[ExecutionEvent]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM execution_events WHERE conversation_id = ? ORDER BY created_at, rowid",
                (conversation_id,),
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
            row = connection.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO app_settings(key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (key, value, _now()),
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
                    "INSERT INTO mcp_connectors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    values,
                )
            else:
                connection.execute(
                    """
                    UPDATE mcp_connectors SET
                        name = ?, transport = ?, endpoint = ?, command = ?, enabled = ?,
                        allowed_tools_json = ?, connection_status = ?, last_error = ?,
                        last_seen = ?, timeout_seconds = ?, created_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (*values[1:], connector.id),
                )

    def get_mcp_connector(self, connector_id: str) -> ConnectorDefinition | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM mcp_connectors WHERE id = ?", (connector_id,)
            ).fetchone()
        return self._connector_from_row(row) if row else None

    def list_mcp_connectors(self) -> list[ConnectorDefinition]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM mcp_connectors ORDER BY updated_at DESC"
            ).fetchall()
        return [self._connector_from_row(row) for row in rows]
