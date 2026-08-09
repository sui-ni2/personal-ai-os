from __future__ import annotations

from datetime import datetime
from typing import Any

from personal_ai_os_mcp import MCPInvocationError, MCPTool
from personal_ai_os_projects import P5Project


class P5MCPServer:
    """Allowlisted, P5-only MCP surface. It has no command or arbitrary path access."""

    id = "p5-project"
    protocol_version = "2026-07-28"

    def __init__(self, project: P5Project) -> None:
        self.project = project

    def tools(self) -> list[MCPTool]:
        issue = {"type": "string", "pattern": "^[0-9]{5,12}$"}
        number = {"type": "string", "pattern": "^[0-9]{5}$"}
        return [
            MCPTool(
                name="p5.status",
                description="Read the isolated P5 daily workflow status and current lock.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                server=self.id,
            ),
            MCPTool(
                name="p5.history",
                description="Read isolated P5 issue and review history.",
                input_schema={
                    "type": "object",
                    "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 200}},
                    "additionalProperties": False,
                },
                server=self.id,
            ),
            MCPTool(
                name="p5.candidate.lookup",
                description="Look up one five-digit candidate inside one P5 issue lock.",
                input_schema={
                    "type": "object",
                    "properties": {"issue": issue, "number": number},
                    "required": ["issue", "number"],
                    "additionalProperties": False,
                },
                server=self.id,
            ),
            MCPTool(
                name="p5.daily.run",
                description=(
                    "After the Beijing 22:22 gate, review a confirmed result and atomically "
                    "lock exactly 10000 candidates for the next P5 issue."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "result_issue": issue,
                        "next_issue": issue,
                        "next_draw_date": {"type": "string", "format": "date"},
                        "official_result": number,
                        "result_confirmed": {"type": "boolean"},
                        "now_beijing": {"type": "string", "format": "date-time"},
                    },
                    "required": [
                        "result_issue",
                        "next_issue",
                        "next_draw_date",
                        "result_confirmed",
                    ],
                    "additionalProperties": False,
                },
                server=self.id,
            ),
            MCPTool(
                name="p5.audit",
                description="Read P5 model rules, cumulative evidence, and append-only audit events.",
                input_schema={
                    "type": "object",
                    "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 500}},
                    "additionalProperties": False,
                },
                server=self.id,
            ),
        ]

    async def _call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        allowed = {tool.name for tool in self.tools()}
        if name not in allowed:
            raise MCPInvocationError(f"Unknown P5 tool: {name}")
        if name == "p5.status":
            if arguments:
                raise MCPInvocationError("p5.status accepts no arguments")
            result = self.project.store.home()
        elif name == "p5.history":
            if set(arguments) - {"limit"}:
                raise MCPInvocationError("p5.history accepts only limit")
            result = {"items": self.project.store.history(int(arguments.get("limit", 50)))}
        elif name == "p5.candidate.lookup":
            if set(arguments) != {"issue", "number"}:
                raise MCPInvocationError("p5.candidate.lookup requires issue and number")
            result = self.project.store.candidate(
                str(arguments["issue"]), str(arguments["number"])
            )
        elif name == "p5.daily.run":
            allowed_args = {
                "result_issue",
                "next_issue",
                "next_draw_date",
                "official_result",
                "result_confirmed",
                "now_beijing",
            }
            if set(arguments) - allowed_args:
                raise MCPInvocationError("p5.daily.run received unknown arguments")
            required = {"result_issue", "next_issue", "next_draw_date", "result_confirmed"}
            if not required.issubset(arguments):
                raise MCPInvocationError("p5.daily.run is missing required arguments")
            now = arguments.get("now_beijing")
            result = self.project.store.run_daily(
                result_issue=str(arguments["result_issue"]),
                next_issue=str(arguments["next_issue"]),
                next_draw_date=str(arguments["next_draw_date"]),
                official_result=(
                    str(arguments["official_result"])
                    if arguments.get("official_result") is not None
                    else None
                ),
                result_confirmed=bool(arguments["result_confirmed"]),
                now_beijing=datetime.fromisoformat(str(now)) if now else None,
            )
        else:
            if set(arguments) - {"limit"}:
                raise MCPInvocationError("p5.audit accepts only limit")
            result = self.project.store.audit(int(arguments.get("limit", 100)))
        return {"content": [{"type": "json", "json": result}], "isError": False}

    async def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = payload.get("id")
        if payload.get("jsonrpc") != "2.0" or request_id is None:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32600, "message": "Invalid Request"},
            }
        method = payload.get("method")
        if method == "server/discover":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {"tools": {}},
                },
            }
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.input_schema,
                        }
                        for tool in self.tools()
                    ]
                },
            }
        if method == "tools/call":
            params = payload.get("params") or {}
            try:
                result = await self._call(
                    str(params.get("name") or ""), params.get("arguments") or {}
                )
            except (MCPInvocationError, ValueError, RuntimeError) as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32602, "message": str(exc)},
                }
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": "Method not found"},
        }
