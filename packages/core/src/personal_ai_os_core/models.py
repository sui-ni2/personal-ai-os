from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MemoryStatus(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    INACTIVE = "inactive"
    REJECTED = "rejected"
    STALE = "stale"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    CONFLICT_REVIEW_REQUIRED = "conflict_review_required"


class ProjectStateStatus(StrEnum):
    ACTIVE = "active"
    LOCKED = "locked"
    SUPERSEDED = "superseded"


class Conversation(BaseModel):
    id: str
    title: str
    provider: str
    model: str
    project_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Message(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    tool_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class MemoryRecord(BaseModel):
    id: str
    type: str
    text: str
    source: str
    confidence: float = Field(ge=0, le=1)
    valid_from: datetime | None = None
    status: MemoryStatus = MemoryStatus.ACTIVE
    project_id: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    source_reference: str | None = None
    conflict_key: str | None = None
    last_used_at: datetime | None = None
    why_used: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProjectStateRecord(BaseModel):
    id: str
    project_id: str
    namespace: str
    key: str
    value: dict[str, Any] = Field(default_factory=dict)
    source: str
    status: ProjectStateStatus = ProjectStateStatus.ACTIVE
    version: int = Field(ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Artifact(BaseModel):
    id: str
    kind: Literal["file", "url", "note"]
    locator: str
    title: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RepositoryEvent(BaseModel):
    id: str
    event_type: str
    summary: str
    artifact_id: str | None = None
    project_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
