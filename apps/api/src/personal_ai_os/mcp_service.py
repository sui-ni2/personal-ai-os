from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from personal_ai_os_core import ProjectRegistry
from personal_ai_os_mcp import (
    ConnectionStatus,
    ConnectorDefinition,
    ConnectorRegistry,
    DiscoveredTool,
    MCPInvocationError,
    call_tool,
    discover_tools,
)

from .db import Database


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ExternalMCPService:
    def __init__(
        self,
        database: Database,
        projects: ProjectRegistry,
        registry: ConnectorRegistry,
    ) -> None:
        self.database = database
        self.projects = projects
        self.registry = registry

    def list(self) -> list[ConnectorDefinition]:
        return self.database.list_mcp_connectors()

    def get(self, connector_id: str) -> ConnectorDefinition:
        connector = self.database.get_mcp_connector(connector_id)
        if connector is None:
            raise KeyError(f"Unknown MCP connector: {connector_id}")
        return connector

    def create(self, values: dict[str, Any]) -> ConnectorDefinition:
        candidate = ConnectorDefinition(id="validation", **values)
        self.registry.validate(candidate)
        return self.database.create_mcp_connector(values)

    def update(self, connector_id: str, values: dict[str, Any]) -> ConnectorDefinition:
        current = self.get(connector_id)
        updated = current.model_copy(update=values)
        self.registry.validate(updated)
        status = updated.connection_status
        if not updated.enabled:
            status = ConnectionStatus.DISABLED
        elif not current.enabled and updated.enabled:
            status = ConnectionStatus.CONFIGURED
        updated = updated.model_copy(
            update={"connection_status": status, "updated_at": _now()}
        )
        self.database.save_mcp_connector(updated)
        return updated

    def _set_status(
        self,
        connector: ConnectorDefinition,
        status: ConnectionStatus,
        *,
        error: str | None,
        seen: bool,
    ) -> ConnectorDefinition:
        updated = connector.model_copy(
            update={
                "connection_status": status,
                "last_error": error[:500] if error else None,
                "last_seen": _now() if seen else connector.last_seen,
                "updated_at": _now(),
            }
        )
        self.database.save_mcp_connector(updated)
        return updated

    async def discover(self, connector_id: str) -> list[DiscoveredTool]:
        connector = self.get(connector_id)
        if not connector.enabled:
            raise MCPInvocationError("MCP connector is disabled")
        try:
            transport = self.registry.create_transport(connector)
            tools = await discover_tools(connector.id, transport)
            self._set_status(
                connector, ConnectionStatus.CONNECTED, error=None, seen=True
            )
            return tools
        except Exception as exc:
            error = exc if isinstance(exc, MCPInvocationError) else MCPInvocationError(
                "MCP connector discovery failed"
            )
            self._set_status(
                connector, ConnectionStatus.ERROR, error=str(error), seen=False
            )
            raise error from exc

    async def invoke(
        self,
        project_id: str,
        connector_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        project = self.projects.get(project_id)
        if "external:*" not in project.tools():
            raise MCPInvocationError(
                f"External MCP tools are not permitted for project {project_id}"
            )
        connector = self.get(connector_id)
        if not connector.enabled:
            raise MCPInvocationError("MCP connector is disabled")
        if tool_name not in connector.allowed_tools:
            raise MCPInvocationError(
                f"Tool is not allowlisted for connector {connector_id}: {tool_name}"
            )
        try:
            transport = self.registry.create_transport(connector)
            result = await call_tool(transport, tool_name, arguments)
            self._set_status(
                connector, ConnectionStatus.CONNECTED, error=None, seen=True
            )
            return result
        except Exception as exc:
            error = exc if isinstance(exc, MCPInvocationError) else MCPInvocationError(
                "MCP connector tool call failed"
            )
            self._set_status(
                connector, ConnectionStatus.ERROR, error=str(error), seen=False
            )
            raise error from exc
