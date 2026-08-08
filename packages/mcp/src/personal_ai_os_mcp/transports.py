from __future__ import annotations

import asyncio
import json
import os
import subprocess
from typing import Any, Protocol
from uuid import uuid4

import httpx

from .connectors import DiscoveredTool
from .gateway import MCPInvocationError


PROTOCOL_VERSION = "2026-07-28"


def mcp_request(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    payload_params = dict(params or {})
    payload_params["_meta"] = {
        "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientInfo": {"name": "personal-ai-os", "version": "0.1.0"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    return {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": method,
        "params": payload_params,
    }


def parse_result(response: dict[str, Any]) -> dict[str, Any]:
    if response.get("jsonrpc") != "2.0":
        raise MCPInvocationError("MCP server returned an invalid JSON-RPC response")
    if "error" in response:
        error = response.get("error") or {}
        raise MCPInvocationError(str(error.get("message") or "MCP request failed"))
    result = response.get("result")
    if not isinstance(result, dict):
        raise MCPInvocationError("MCP server response is missing a result object")
    return result


class ExternalMCPTransport(Protocol):
    async def request(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class HTTPMCPTransport:
    def __init__(self, endpoint: str, timeout_seconds: float) -> None:
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    async def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        method = str(payload.get("method") or "")
        headers = {
            "MCP-Protocol-Version": PROTOCOL_VERSION,
            "Mcp-Method": method,
            "Content-Type": "application/json",
        }
        params = payload.get("params") or {}
        if method == "tools/call" and isinstance(params.get("name"), str):
            headers["Mcp-Name"] = params["name"]
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                follow_redirects=False,
            ) as client:
                response = await client.post(self.endpoint, json=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
        except httpx.TimeoutException as exc:
            raise MCPInvocationError("HTTP MCP connector timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise MCPInvocationError(
                f"HTTP MCP connector returned status {exc.response.status_code}"
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise MCPInvocationError("HTTP MCP connector request failed") from exc
        if not isinstance(body, dict):
            raise MCPInvocationError("HTTP MCP connector returned invalid JSON")
        return body


class StdioMCPTransport:
    def __init__(self, argv: tuple[str, ...], timeout_seconds: float) -> None:
        if not argv:
            raise ValueError("stdio MCP command is empty")
        self.argv = argv
        self.timeout_seconds = timeout_seconds

    async def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        process = await asyncio.create_subprocess_exec(
            *self.argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=creationflags,
        )
        try:
            assert process.stdin is not None
            assert process.stdout is not None
            process.stdin.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
            await process.stdin.drain()
            line = await asyncio.wait_for(
                process.stdout.readline(), timeout=self.timeout_seconds
            )
            if not line:
                raise MCPInvocationError("stdio MCP connector closed without a response")
            try:
                response = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise MCPInvocationError("stdio MCP connector returned invalid JSON") from exc
            if not isinstance(response, dict):
                raise MCPInvocationError("stdio MCP connector returned invalid JSON")
            return response
        except TimeoutError as exc:
            raise MCPInvocationError("stdio MCP connector timed out") from exc
        finally:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=1)
                except TimeoutError:
                    process.kill()
                    await process.wait()


async def discover_tools(
    connector_id: str, transport: ExternalMCPTransport
) -> list[DiscoveredTool]:
    response = await transport.request(mcp_request("tools/list"))
    result = parse_result(response)
    tools = result.get("tools")
    if not isinstance(tools, list):
        raise MCPInvocationError("MCP tools/list result is invalid")
    discovered: list[DiscoveredTool] = []
    for item in tools:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise MCPInvocationError("MCP tools/list contains an invalid tool")
        discovered.append(
            DiscoveredTool(
                name=item["name"],
                description=str(item.get("description") or ""),
                input_schema=item.get("inputSchema")
                if isinstance(item.get("inputSchema"), dict)
                else {},
                connector_id=connector_id,
            )
        )
    return discovered


async def call_tool(
    transport: ExternalMCPTransport, tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    response = await transport.request(
        mcp_request("tools/call", {"name": tool_name, "arguments": arguments})
    )
    return parse_result(response)
