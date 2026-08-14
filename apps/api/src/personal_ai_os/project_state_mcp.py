from __future__ import annotations

from typing import Any

from personal_ai_os_mcp import MCPInvocationError, MCPTool

from .db import Database
from .project_state import ProjectStateConflict, ProjectStateService
from .project_workflow import ProjectWorkflowConflict, ProjectWorkflowService


PROJECT_STATE_TOOL_NAMES = {
    "project.state.snapshot",
    "project.state.history",
    "project.state.put",
    "project.experience.append",
    "project.workflow.list",
    "project.workflow.create",
    "project.workflow.advance",
    "project.workflow.transitions",
}


class ProjectStateMCPServer:
    """Project-bound MCP surface for private state and workflow continuity.

    The active project is injected by MCPGateway metadata. No tool accepts a caller-provided
    project_id, preventing a model from selecting another project's private database.
    """

    id = "project-private-state"
    protocol_version = "2026-07-28"

    def __init__(self, database: Database, *, data_dir, tenant_id: str) -> None:
        self.state = ProjectStateService(
            database,
            data_dir=data_dir,
            tenant_id=tenant_id,
        )
        self.workflow = ProjectWorkflowService(
            database,
            data_dir=data_dir,
            tenant_id=tenant_id,
        )

    def tools(self) -> list[MCPTool]:
        safe_name = {"type": "string", "pattern": "^[A-Za-z0-9_.-]+$", "maxLength": 120}
        source = {"type": "string", "minLength": 1, "maxLength": 500}
        confidence = {"type": "number", "minimum": 0, "maximum": 1}
        return [
            MCPTool(
                name="project.state.snapshot",
                description="Read private persistent state and experience for the active project only.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                server=self.id,
            ),
            MCPTool(
                name="project.state.history",
                description="Read prior versions of private state for the active project only.",
                input_schema={
                    "type": "object",
                    "properties": {"namespace": safe_name, "key": safe_name},
                    "additionalProperties": False,
                },
                server=self.id,
            ),
            MCPTool(
                name="project.state.put",
                description="Create or version one private state record for the active project, with optional lock protection.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "namespace": safe_name,
                        "key": safe_name,
                        "value": {"type": "object"},
                        "source": source,
                        "confidence": confidence,
                        "lock": {"type": "boolean"},
                        "expected_version": {"type": "integer", "minimum": 0},
                        "supersede_locked": {"type": "boolean"},
                    },
                    "required": ["namespace", "key", "value", "source"],
                    "additionalProperties": False,
                },
                server=self.id,
            ),
            MCPTool(
                name="project.experience.append",
                description="Append private cumulative experience for the active project without replacing prior evidence.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "namespace": safe_name,
                        "text": {"type": "string", "minLength": 1, "maxLength": 50000},
                        "source": source,
                        "confidence": confidence,
                    },
                    "required": ["namespace", "text", "source", "confidence"],
                    "additionalProperties": False,
                },
                server=self.id,
            ),
            MCPTool(
                name="project.workflow.list",
                description="Read private workflow runs and their required next gates for the active project.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                server=self.id,
            ),
            MCPTool(
                name="project.workflow.create",
                description="Create one ordered private workflow run for the active project.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "workflow_id": safe_name,
                        "run_key": safe_name,
                        "steps": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 64,
                            "uniqueItems": True,
                            "items": {"type": "string", "pattern": "^[A-Za-z0-9_.-]+$", "maxLength": 80},
                        },
                        "source": source,
                    },
                    "required": ["workflow_id", "run_key", "steps", "source"],
                    "additionalProperties": False,
                },
                server=self.id,
            ),
            MCPTool(
                name="project.workflow.advance",
                description="Advance an active project's private workflow by exactly its required next step.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "workflow_id": safe_name,
                        "run_key": safe_name,
                        "next_step": safe_name,
                        "expected_version": {"type": "integer", "minimum": 1},
                        "evidence": {"type": "object"},
                        "source": source,
                    },
                    "required": ["workflow_id", "run_key", "next_step", "expected_version", "evidence", "source"],
                    "additionalProperties": False,
                },
                server=self.id,
            ),
            MCPTool(
                name="project.workflow.transitions",
                description="Read append-only workflow transition receipts for the active project.",
                input_schema={
                    "type": "object",
                    "properties": {"workflow_id": safe_name, "run_key": safe_name},
                    "required": ["workflow_id", "run_key"],
                    "additionalProperties": False,
                },
                server=self.id,
            ),
        ]

    @staticmethod
    def _project_id(params: dict[str, Any]) -> str:
        meta = params.get("_meta") or {}
        project_id = meta.get("io.personal-ai-os/projectId")
        if not isinstance(project_id, str) or not project_id:
            raise MCPInvocationError("Active project binding is missing")
        return project_id

    @staticmethod
    def _json_result(value: Any) -> dict[str, Any]:
        return {"content": [{"type": "json", "json": value}], "isError": False}

    async def _call(
        self,
        name: str,
        arguments: dict[str, Any],
        project_id: str,
    ) -> dict[str, Any]:
        if name not in PROJECT_STATE_TOOL_NAMES:
            raise MCPInvocationError(f"Unknown private project-state tool: {name}")

        if name == "project.state.snapshot":
            if arguments:
                raise MCPInvocationError("project.state.snapshot accepts no arguments")
            return self._json_result(self.state.snapshot(project_id).as_context())

        if name == "project.state.history":
            if set(arguments) - {"namespace", "key"}:
                raise MCPInvocationError("project.state.history received unknown arguments")
            return self._json_result(
                {
                    "items": self.state.list_history(
                        project_id,
                        namespace=arguments.get("namespace"),
                        key=arguments.get("key"),
                    )
                }
            )

        if name == "project.state.put":
            allowed = {
                "namespace",
                "key",
                "value",
                "source",
                "confidence",
                "lock",
                "expected_version",
                "supersede_locked",
            }
            if set(arguments) - allowed:
                raise MCPInvocationError("project.state.put received unknown arguments")
            required = {"namespace", "key", "value", "source"}
            if not required.issubset(arguments):
                raise MCPInvocationError("project.state.put is missing required arguments")
            return self._json_result(
                self.state.put_state(
                    project_id=project_id,
                    namespace=str(arguments["namespace"]),
                    key=str(arguments["key"]),
                    value=dict(arguments["value"]),
                    source=str(arguments["source"]),
                    confidence=float(arguments.get("confidence", 1.0)),
                    lock=bool(arguments.get("lock", False)),
                    expected_version=(
                        int(arguments["expected_version"])
                        if arguments.get("expected_version") is not None
                        else None
                    ),
                    supersede_locked=bool(arguments.get("supersede_locked", False)),
                )
            )

        if name == "project.experience.append":
            if set(arguments) != {"namespace", "text", "source", "confidence"}:
                raise MCPInvocationError(
                    "project.experience.append requires namespace, text, source, and confidence"
                )
            return self._json_result(
                self.state.append_experience(
                    project_id=project_id,
                    namespace=str(arguments["namespace"]),
                    text=str(arguments["text"]),
                    source=str(arguments["source"]),
                    confidence=float(arguments["confidence"]),
                )
            )

        if name == "project.workflow.list":
            if arguments:
                raise MCPInvocationError("project.workflow.list accepts no arguments")
            return self._json_result({"items": self.workflow.list_workflows(project_id)})

        if name == "project.workflow.create":
            if set(arguments) != {"workflow_id", "run_key", "steps", "source"}:
                raise MCPInvocationError(
                    "project.workflow.create requires workflow_id, run_key, steps, and source"
                )
            return self._json_result(
                self.workflow.create_workflow(
                    project_id=project_id,
                    workflow_id=str(arguments["workflow_id"]),
                    run_key=str(arguments["run_key"]),
                    steps=[str(step) for step in arguments["steps"]],
                    source=str(arguments["source"]),
                )
            )

        if name == "project.workflow.advance":
            required = {
                "workflow_id",
                "run_key",
                "next_step",
                "expected_version",
                "evidence",
                "source",
            }
            if set(arguments) != required:
                raise MCPInvocationError(
                    "project.workflow.advance requires workflow_id, run_key, next_step, expected_version, evidence, and source"
                )
            return self._json_result(
                self.workflow.advance_workflow(
                    project_id=project_id,
                    workflow_id=str(arguments["workflow_id"]),
                    run_key=str(arguments["run_key"]),
                    next_step=str(arguments["next_step"]),
                    expected_version=int(arguments["expected_version"]),
                    evidence=dict(arguments["evidence"]),
                    source=str(arguments["source"]),
                )
            )

        if set(arguments) != {"workflow_id", "run_key"}:
            raise MCPInvocationError(
                "project.workflow.transitions requires workflow_id and run_key"
            )
        return self._json_result(
            {
                "items": self.workflow.list_transitions(
                    project_id,
                    str(arguments["workflow_id"]),
                    str(arguments["run_key"]),
                )
            }
        )

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
                project_id = self._project_id(params)
                result = await self._call(
                    str(params.get("name") or ""),
                    params.get("arguments") or {},
                    project_id,
                )
            except (MCPInvocationError, ProjectStateConflict, ProjectWorkflowConflict, ValueError, TypeError) as exc:
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
