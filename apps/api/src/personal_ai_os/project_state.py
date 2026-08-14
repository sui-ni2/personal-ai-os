from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from personal_ai_os_core import MemoryStatus

from .db import Database


STATE_PREFIX = "project_state"
EXPERIENCE_PREFIX = "project_experience"
MAX_CONTEXT_RECORDS = 80
MAX_CONTEXT_CHARS = 40_000


def _state_type(namespace: str, key: str) -> str:
    return f"{STATE_PREFIX}:{namespace}:{key}"


def _experience_type(namespace: str) -> str:
    return f"{EXPERIENCE_PREFIX}:{namespace}"


@dataclass(frozen=True)
class ProjectStateSnapshot:
    project_id: str
    states: list[dict[str, Any]]
    experiences: list[dict[str, Any]]

    def as_context(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "states": self.states,
            "experiences": self.experiences,
        }


class ProjectStateService:
    """Project-scoped persistent state built on the existing private Memory store.

    The implementation is intentionally domain-agnostic. Public source code defines only the
    storage protocol; real project values remain in the runtime SQLite database, which is gitignored.
    """

    def __init__(self, database: Database) -> None:
        self.database = database

    def _project_memories(self, project_id: str):
        return [
            item
            for item in self.database.list_memories(status=MemoryStatus.ACTIVE.value)
            if item.project_id == project_id
        ]

    def list_state(self, project_id: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for record in self._project_memories(project_id):
            if not record.type.startswith(f"{STATE_PREFIX}:"):
                continue
            _, namespace, key = record.type.split(":", 2)
            try:
                value = json.loads(record.text)
            except json.JSONDecodeError:
                value = {"raw": record.text, "invalid_json": True}
            items.append(
                {
                    "id": record.id,
                    "namespace": namespace,
                    "key": key,
                    "value": value,
                    "source": record.source,
                    "confidence": record.confidence,
                    "updated_at": record.updated_at.isoformat(),
                }
            )
        items.sort(key=lambda item: (item["namespace"], item["key"]))
        return items

    def put_state(
        self,
        *,
        project_id: str,
        namespace: str,
        key: str,
        value: dict[str, Any],
        source: str,
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        record_type = _state_type(namespace, key)
        current = next(
            (item for item in self._project_memories(project_id) if item.type == record_type),
            None,
        )
        payload = {
            "type": record_type,
            "text": json.dumps(value, ensure_ascii=False, separators=(",", ":")),
            "source": source,
            "confidence": confidence,
            "status": MemoryStatus.ACTIVE,
            "project_id": project_id,
        }
        if current is None:
            record = self.database.create_memory(payload)
        else:
            record = self.database.update_memory(current.id, payload)
            assert record is not None
        self.database.add_repository_event(
            event_type="project_state.updated",
            summary=f"Updated project state {namespace}/{key}",
            project_id=project_id,
            details={"namespace": namespace, "key": key, "memory_id": record.id},
        )
        return {
            "id": record.id,
            "project_id": project_id,
            "namespace": namespace,
            "key": key,
            "value": value,
            "source": record.source,
            "confidence": record.confidence,
            "updated_at": record.updated_at.isoformat(),
        }

    def append_experience(
        self,
        *,
        project_id: str,
        namespace: str,
        text: str,
        source: str,
        confidence: float,
    ) -> dict[str, Any]:
        record = self.database.create_memory(
            {
                "type": _experience_type(namespace),
                "text": text,
                "source": source,
                "confidence": confidence,
                "status": MemoryStatus.ACTIVE,
                "project_id": project_id,
            }
        )
        self.database.add_repository_event(
            event_type="project_experience.appended",
            summary=f"Appended project experience in {namespace}",
            project_id=project_id,
            details={"namespace": namespace, "memory_id": record.id},
        )
        return record.model_dump(mode="json")

    def list_experience(self, project_id: str) -> list[dict[str, Any]]:
        items = []
        for record in self._project_memories(project_id):
            if not record.type.startswith(f"{EXPERIENCE_PREFIX}:"):
                continue
            namespace = record.type.split(":", 1)[1]
            items.append(
                {
                    "id": record.id,
                    "namespace": namespace,
                    "text": record.text,
                    "source": record.source,
                    "confidence": record.confidence,
                    "updated_at": record.updated_at.isoformat(),
                }
            )
        items.sort(key=lambda item: item["updated_at"], reverse=True)
        return items

    def snapshot(self, project_id: str) -> ProjectStateSnapshot:
        return ProjectStateSnapshot(
            project_id=project_id,
            states=self.list_state(project_id)[:MAX_CONTEXT_RECORDS],
            experiences=self.list_experience(project_id)[:MAX_CONTEXT_RECORDS],
        )

    def context_json(self, project_id: str) -> str:
        raw = json.dumps(self.snapshot(project_id).as_context(), ensure_ascii=False)
        if len(raw) <= MAX_CONTEXT_CHARS:
            return raw
        return raw[:MAX_CONTEXT_CHARS] + '"truncated":true}'
