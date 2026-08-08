from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConnectorTransport(StrEnum):
    HTTP = "http"
    STDIO = "stdio"


class ConnectionStatus(StrEnum):
    DISABLED = "disabled"
    CONFIGURED = "configured"
    CONNECTED = "connected"
    ERROR = "error"


class ConnectorDefinition(BaseModel):
    id: str
    name: str
    transport: ConnectorTransport
    endpoint: str | None = None
    command: str | None = None
    enabled: bool = True
    allowed_tools: list[str] = Field(default_factory=list)
    connection_status: ConnectionStatus = ConnectionStatus.CONFIGURED
    last_error: str | None = None
    last_seen: datetime | None = None
    timeout_seconds: float = Field(default=15, ge=0.1, le=120)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DiscoveredTool(BaseModel):
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    connector_id: str
