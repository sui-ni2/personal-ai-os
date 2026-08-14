from __future__ import annotations

from typing import Any, Literal, Protocol
from uuid import uuid4

from personal_ai_os_core import ProjectRegistry
from pydantic import BaseModel, Field


class MCPTool(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    server: str
    audit_result: Literal["bounded", "metadata_only"] = "bounded"


class MCPServer(Protocol):
    id: str

    def tools(self) -> list[MCPTool]: ...

    async def request(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class MCPInvocationError(RuntimeError):
    pass


class EchoMCPServer:
    """A no-I/O, stateless JSON-RPC MCP reference server for gateway verification."""

    id = "local-reference"
    protocol_version = "2026-07-28"

    def tools(self) -> list[MCPTool]:
        return [
            MCPTool(
                name="system.echo",
                description="Return a caller-provided message for MCP trace verification.",
                input_schema={
                    "type": "object",
                    "properties": {"message": {"type": "string", "maxLength": 2000}},
                    "required": ["message"],
                    "additionalProperties": False,
                },
                server=self.id,
            )
        ]

    async def _call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name != "system.echo":
            raise MCPInvocationError(f"Unknown tool: {tool_name}")
        if set(arguments) != {"message"} or not isinstance(arguments.get("message"), str):
            raise MCPInvocationError("system.echo requires one string field: message")
        if len(arguments["message"]) > 2000:
            raise MCPInvocationError("system.echo message exceeds 2000 characters")
        return {"content": [{"type": "text", "text": arguments["message"]}], "isError": False}

    async def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("id")
        if payload.get("jsonrpc") != "2.0" or request_id is None:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32600, "message": "Invalid Request"}}
        method = payload.get("method")
        if method == "server/discover":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"protocolVersion": self.protocol_version, "capabilities": {"tools": {}}},
            }
        if method == "tools/list":
            tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                }
                for tool in self.tools()
            ]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
        if method == "tools/call":
            params = payload.get("params") or {}
            try:
                result = await self._call(params.get("name"), params.get("arguments") or {})
            except MCPInvocationError as exc:
                return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": str(exc)}}
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}


class MCPGateway:
    def __init__(
        self,
        projects: ProjectRegistry,
        servers: list[MCPServer],
        *,
        shared_project_tools: dict[str, set[str]] | None = None,
        metadata_only_tools: set[str] | None = None,
    ) -> None:
        self._projects = projects
        self._servers = {server.id: server for server in servers}
        self._shared_project_tools = {
            project_id: frozenset(names)
            for project_id, names in (shared_project_tools or {}).items()
        }
        self._metadata_only_tools = frozenset(metadata_only_tools or set())
        self._tools: dict[str, tuple[MCPServer, MCPTool]] = {}
        for server in servers:
            for tool in server.tools():
                if tool.name in self._tools:
                    raise ValueError(f"Duplicate MCP tool: {tool.name}")
                self._tools[tool.name] = (server, tool)
        registered = set(self._tools)
        for project_id, names in self._shared_project_tools.items():
            self._projects.get(project_id)
            missing = set(names) - registered
            if missing:
                raise ValueError(
                    f"Shared project tools are not registered for {project_id}: {sorted(missing)}"
                )
        missing_audit_tools = set(self._metadata_only_tools) - registered
        if missing_audit_tools:
            raise ValueError(
                f"Metadata-only tools are not registered: {sorted(missing_audit_tools)}"
            )

    def _allowed_tools(self, project_id: str) -> set[str]:
        return set(self._projects.get(project_id).tools()) | set(
            self._shared_project_tools.get(project_id, frozenset())
        )

    def list_tools(self, project_id: str) -> list[MCPTool]:
        allowed = self._allowed_tools(project_id)
        return [tool for name, (_, tool) in self._tools.items() if name in allowed]

    def audit_result_policy(self, project_id: str, tool_name: str) -> Literal["bounded", "metadata_only"]:
        if tool_name not in self._allowed_tools(project_id):
            raise MCPInvocationError(f"Tool is not permitted for project {project_id}: {tool_name}")
        try:
            _, tool = self._tools[tool_name]
        except KeyError as exc:
            raise MCPInvocationError(f"Tool is not registered: {tool_name}") from exc
        if tool_name in self._metadata_only_tools:
            return "metadata_only"
        return tool.audit_result

    async def invoke(self, project_id: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name not in self._allowed_tools(project_id):
            raise MCPInvocationError(f"Tool is not permitted for project {project_id}: {tool_name}")
        try:
            server, _ = self._tools[tool_name]
        except KeyError as exc:
            raise MCPInvocationError(f"Tool is not registered: {tool_name}") from exc
        response = await server.request(
            {
                "jsonrpc": "2.0",
                "id": str(uuid4()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                    "_meta": {
                        "io.modelcontextprotocol/clientInfo": {
                            "name": "personal-ai-os",
                            "version": "0.1.0",
                        },
                        "io.personal-ai-os/projectId": project_id,
                    },
                },
            }
        )
        if "error" in response:
            raise MCPInvocationError(response["error"].get("message", "MCP request failed"))
        result = response["result"]
        if self.audit_result_policy(project_id, tool_name) == "metadata_only":
            if isinstance(result, dict):
                return {"_audit_policy": "metadata_only", **result}
            return {"_audit_policy": "metadata_only", "content": result}
        return result
