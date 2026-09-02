from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from personal_ai_os_core import MemoryStatus
from pydantic import BaseModel, Field, field_validator, model_validator


_SAFE_WORKFLOW_VALUE = re.compile(r"^[A-Za-z0-9_.-]+$")


class ToolRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    connector_id: str | None = None
    confirmation_id: str | None = Field(default=None, min_length=1, max_length=128)


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    provider: str
    model: str
    project_id: str = "general"
    content: str = Field(min_length=1, max_length=100_000)
    tool: ToolRequest | None = None
    send_scope_receipt_id: str | None = Field(default=None, min_length=1, max_length=128)
    allow_fallback: bool = False


class SendScopePreviewRequest(BaseModel):
    provider: str
    model: str
    project_id: str = "general"
    content: str = Field(min_length=1, max_length=100_000)
    conversation_id: str | None = None
    tool: ToolRequest | None = None


class ToolActionPreviewRequest(BaseModel):
    project_id: str = "general"
    connector_id: str = Field(min_length=1, max_length=128)
    tool_name: str = Field(min_length=1, max_length=200)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolActionConfirmation(BaseModel):
    confirmed: Literal[True]


class BudgetPolicyUpdate(BaseModel):
    scope_type: Literal["tenant", "project"]
    scope_id: str = Field(min_length=1, max_length=120)
    period: Literal["daily", "weekly", "monthly"]
    limit_tokens: int = Field(ge=1, le=10_000_000_000)
    warn_percent: int = Field(default=80, ge=1, le=100)
    hard_limit: bool = True


class RoutingSettingsUpdate(BaseModel):
    policy: Literal["STRICT_PROVIDER", "FALLBACK_ALLOWED", "ASK_BEFORE_FALLBACK"]
    fallback_provider: str | None = Field(default=None, max_length=80)
    fallback_model: str | None = Field(default=None, max_length=200)


class ConversationCreate(BaseModel):
    provider: str
    model: str
    project_id: str = "general"
    title: str = Field(default="New conversation", min_length=1, max_length=120)


class RealtimeTranscriptCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("content must not be blank")
        return normalized


class MemoryCreate(BaseModel):
    type: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=50_000)
    source: str = Field(min_length=1, max_length=500)
    confidence: float = Field(default=1, ge=0, le=1)
    valid_from: datetime | None = None
    status: MemoryStatus = MemoryStatus.ACTIVE
    project_id: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    source_reference: str | None = Field(default=None, max_length=500)
    conflict_key: str | None = Field(default=None, max_length=160)


class MemoryUpdate(BaseModel):
    type: str | None = Field(default=None, min_length=1, max_length=80)
    text: str | None = Field(default=None, min_length=1, max_length=50_000)
    source: str | None = Field(default=None, min_length=1, max_length=500)
    confidence: float | None = Field(default=None, ge=0, le=1)
    valid_from: datetime | None = None
    status: MemoryStatus | None = None
    project_id: str | None = None
    provenance: dict[str, Any] | None = None
    source_reference: str | None = Field(default=None, max_length=500)
    conflict_key: str | None = Field(default=None, max_length=160)
    why_used: str | None = Field(default=None, max_length=500)


class MemoryConflictResolution(BaseModel):
    action: Literal["keep_existing", "replace", "merge", "keep_both"]
    scope_project_id: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")


class ProjectStatePut(BaseModel):
    namespace: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    key: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.-]+$")
    value: dict[str, Any] = Field(default_factory=dict)
    source: str = Field(min_length=1, max_length=500)
    confidence: float = Field(default=1, ge=0, le=1)
    lock: bool = False
    expected_version: int | None = Field(default=None, ge=0)
    supersede_locked: bool = False


class UserProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    project_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )


class ProjectExperienceAppend(BaseModel):
    namespace: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    text: str = Field(min_length=1, max_length=50_000)
    source: str = Field(min_length=1, max_length=500)
    confidence: float = Field(default=1, ge=0, le=1)


class ProjectRecoveryCheckpoint(BaseModel):
    expected_version: int = Field(ge=1)


class ProjectRecoverySessionClose(BaseModel):
    expected_version: int = Field(ge=1)


class ProjectRecoveryConfirm(BaseModel):
    expected_version: int = Field(ge=1)


class ProjectWorkflowCreate(BaseModel):
    workflow_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    run_key: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.-]+$")
    steps: list[str] = Field(min_length=1, max_length=64)
    source: str = Field(min_length=1, max_length=500)

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("workflow steps must be unique")
        if any(
            not step
            or len(step) > 80
            or _SAFE_WORKFLOW_VALUE.fullmatch(step) is None
            for step in value
        ):
            raise ValueError("workflow steps must use only letters, numbers, dot, underscore, or hyphen")
        return value


class ProjectWorkflowAdvance(BaseModel):
    next_step: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    expected_version: int = Field(ge=1)
    evidence: dict[str, Any] = Field(default_factory=dict)
    source: str = Field(min_length=1, max_length=500)


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
    connector_id: str | None = None
    confirmation_id: str | None = Field(default=None, min_length=1, max_length=128)


class MCPConnectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    transport: Literal["http", "stdio"]
    endpoint: str | None = Field(default=None, max_length=2000)
    command: str | None = Field(default=None, max_length=120)
    enabled: bool = True
    allowed_tools: list[str] = Field(default_factory=list, max_length=100)
    timeout_seconds: float = Field(default=15, ge=0.1, le=120)

    @field_validator("allowed_tools")
    @classmethod
    def validate_allowed_tools(cls, value: list[str]) -> list[str]:
        if any(not item or len(item) > 200 or "*" in item for item in value):
            raise ValueError("allowed_tools must contain exact non-wildcard tool names")
        if len(set(value)) != len(value):
            raise ValueError("allowed_tools must not contain duplicates")
        return value

    @model_validator(mode="after")
    def validate_transport_target(self):
        if self.transport == "http" and not self.endpoint:
            raise ValueError("HTTP connector requires endpoint")
        if self.transport == "stdio" and not self.command:
            raise ValueError("stdio connector requires command alias")
        return self


class MCPConnectorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    endpoint: str | None = Field(default=None, max_length=2000)
    command: str | None = Field(default=None, max_length=120)
    enabled: bool | None = None
    allowed_tools: list[str] | None = Field(default=None, max_length=100)
    timeout_seconds: float | None = Field(default=None, ge=0.1, le=120)

    @field_validator("allowed_tools")
    @classmethod
    def validate_allowed_tools(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and any(
            not item or len(item) > 200 or "*" in item for item in value
        ):
            raise ValueError("allowed_tools must contain exact non-wildcard tool names")
        if value is not None and len(set(value)) != len(value):
            raise ValueError("allowed_tools must not contain duplicates")
        return value


class SettingsUpdate(BaseModel):
    default_provider: str | None = None
    default_model: str | None = None
