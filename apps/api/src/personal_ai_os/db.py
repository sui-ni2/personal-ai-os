from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from personal_ai_os_core import Artifact, Conversation, MemoryRecord, Message, MessageRole, RepositoryEvent


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
    )
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
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {row["version"] for row in connection.execute("SELECT version FROM schema_migrations")}
            for version, sql in MIGRATIONS:
                if version in applied:
                    continue
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

    def list_conversations(self) -> list[Conversation]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
        return [Conversation(**dict(row)) for row in rows]

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
