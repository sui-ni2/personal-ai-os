from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from .models import utc_now


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

    def public_payload(self) -> dict[str, Any]:
        """Return auditable facts only; no hidden reasoning is represented here."""
        return self.model_dump(mode="json")
