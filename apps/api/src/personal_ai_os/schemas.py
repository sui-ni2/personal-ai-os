from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from personal_ai_os_core import MemoryStatus
from pydantic import BaseModel, Field


class ToolRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    provider: str
    model: str
    project_id: str = "general"
    content: str = Field(min_length=1, max_length=100_000)
    tool: ToolRequest | None = None


class MemoryCreate(BaseModel):
    type: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=50_000)
    source: str = Field(min_length=1, max_length=500)
    confidence: float = Field(default=1, ge=0, le=1)
    valid_from: datetime | None = None
    status: MemoryStatus = MemoryStatus.ACTIVE
    project_id: str | None = None


class MemoryUpdate(BaseModel):
    type: str | None = Field(default=None, min_length=1, max_length=80)
    text: str | None = Field(default=None, min_length=1, max_length=50_000)
    source: str | None = Field(default=None, min_length=1, max_length=500)
    confidence: float | None = Field(default=None, ge=0, le=1)
    valid_from: datetime | None = None
    status: MemoryStatus | None = None
    project_id: str | None = None


class ArtifactCreate(BaseModel):
    kind: Literal["file", "url", "note"]
    locator: str = Field(min_length=1, max_length=4000)
    title: str = Field(min_length=1, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None


class MCPInvokeRequest(BaseModel):
    project_id: str = "general"
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class SettingsUpdate(BaseModel):
    default_provider: str | None = None
    default_model: str | None = None
