from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .models import utc_now


_MAX_AUDIT_DEPTH = 5
_MAX_AUDIT_ITEMS = 50
_MAX_AUDIT_STRING = 4_000
_REDACTED = "[redacted]"
_TRUNCATED = "[truncated]"
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")
_PROVIDER_KEY_PATTERN = re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{12,}\b", re.IGNORECASE)
_NAMED_SECRET_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|session[_-]?token|token|password|secret)=([^&\s]+)"
)


def _sensitive_audit_key(key: str) -> bool:
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    normalized = re.sub(r"[^a-z0-9]+", "_", separated.lower()).strip("_")
    parts = set(normalized.split("_"))
    if parts & {
        "authorization",
        "cookie",
        "credential",
        "exception",
        "password",
        "reasoning",
        "secret",
        "stacktrace",
        "thought",
        "traceback",
    }:
        return True
    return (
        normalized in {"key", "token", "trace", "stack"}
        or {"api", "key"}.issubset(parts)
        or {"access", "token"}.issubset(parts)
        or {"refresh", "token"}.issubset(parts)
        or {"session", "token"}.issubset(parts)
        or {"private", "key"}.issubset(parts)
        or {"stack", "trace"}.issubset(parts)
    )


def _sanitize_audit_string(value: str) -> str:
    sanitized = _BEARER_PATTERN.sub(_REDACTED, value)
    sanitized = _PROVIDER_KEY_PATTERN.sub(_REDACTED, sanitized)
    sanitized = _NAMED_SECRET_PATTERN.sub(
        lambda match: f"{match.group(1)}={_REDACTED}", sanitized
    )
    if len(sanitized) > _MAX_AUDIT_STRING:
        return sanitized[:_MAX_AUDIT_STRING] + _TRUNCATED
    return sanitized


def _sanitize_audit_value(value: Any, depth: int = 0) -> Any:
    if depth >= _MAX_AUDIT_DEPTH:
        return _TRUNCATED
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _sanitize_audit_string(value)
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= _MAX_AUDIT_ITEMS:
                break
            label = str(key)
            sanitized[label] = (
                _REDACTED
                if _sensitive_audit_key(label)
                else _sanitize_audit_value(item, depth + 1)
            )
        if len(value) > _MAX_AUDIT_ITEMS:
            sanitized["_truncated_items"] = len(value) - _MAX_AUDIT_ITEMS
        return sanitized
    if isinstance(value, (list, tuple)):
        items = [_sanitize_audit_value(item, depth + 1) for item in value[:_MAX_AUDIT_ITEMS]]
        if len(value) > _MAX_AUDIT_ITEMS:
            items.append(_TRUNCATED)
        return items
    return f"[{type(value).__name__}]"


class EventType(StrEnum):
    MESSAGE = "message"
    TOOL_START = "tool_start"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    DONE = "done"


class ExecutionEvent(BaseModel):
    id: str
    type: EventType
    status: Literal["started", "running", "succeeded", "failed"]
    conversation_id: str | None = None
    tool: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("payload", mode="before")
    @classmethod
    def sanitize_payload(cls, value: Any) -> dict[str, Any]:
        sanitized = _sanitize_audit_value(value or {})
        return sanitized if isinstance(sanitized, dict) else {}

    def public_payload(self) -> dict[str, Any]:
        """Return auditable facts only; no hidden reasoning is represented here."""
        return self.model_dump(mode="json")
