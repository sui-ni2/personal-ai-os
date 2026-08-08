from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

import pytest
from fastapi.testclient import TestClient
from personal_ai_os_mcp import EchoMCPServer

from personal_ai_os.main import create_app
from personal_ai_os.chat import stream_chat
from personal_ai_os.schemas import ChatRequest


class _HTTPMCPHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        request = json.loads(self.rfile.read(length))
        assert self.headers["MCP-Protocol-Version"] == "2026-07-28"
        assert self.headers["Mcp-Method"] == request.get("method")
        assert request["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"] == "2026-07-28"
        params = request.get("params") or {}
        if request.get("method") == "tools/list":
            result: dict[str, Any] = {
                "tools": [
                    {
                        "name": "external.echo",
                        "description": "Echo from the HTTP connector.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"message": {"type": "string"}},
                            "required": ["message"],
                        },
                    }
                ]
            }
        elif request.get("method") == "tools/call":
            message = str((params.get("arguments") or {}).get("message") or "")
            result = {"content": [{"type": "text", "text": f"http:{message}"}]}
        else:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(
            {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
        ).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class _HTTPMCPServer:
    def __enter__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _HTTPMCPHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.endpoint = f"http://{host}:{port}/mcp"
        return self

    def __exit__(self, *args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def _sse_data(body: str) -> list[dict[str, object]]:
    return [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]


def test_health_and_secret_redaction(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "version": "0.1.0"}
    settings = client.get("/api/settings").json()
    assert settings["secrets"] == {"storage": "environment", "values_exposed": False}
    assert "api_key" not in json.dumps(settings).lower()
    switched = client.patch("/api/settings", json={"default_provider": "anthropic"})
    assert switched.status_code == 200
    assert switched.json()["default_model"] == "anthropic-test"
    assert client.patch("/api/settings", json={"default_model": "not-allowlisted"}).status_code == 400


def test_database_migrations_are_current(client: TestClient, runtime) -> None:
    assert client.get("/health").status_code == 200
    with runtime.database.connect() as connection:
        versions = [
            row["version"]
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
        ]
    assert versions == [1, 2, 3]


def test_memory_and_repository_persist(client: TestClient) -> None:
    response = client.post(
        "/api/memory",
        json={
            "type": "preference",
            "text": "Use concise status updates.",
            "source": "user",
            "confidence": 1,
            "project_id": "general",
        },
    )
    assert response.status_code == 201
    memory_id = response.json()["id"]
    assert client.get("/api/memory?status=active").json()["items"][0]["id"] == memory_id
    timeline = client.get("/api/repository/timeline").json()["items"]
    assert timeline[0]["event_type"] == "memory.created"
    assert client.patch(f"/api/memory/{memory_id}", json={"status": "inactive"}).status_code == 200


def test_mcp_reference_connector(client: TestClient) -> None:
    tools = client.get("/api/mcp/tools?project_id=general").json()["items"]
    assert [tool["name"] for tool in tools] == ["system.echo"]
    response = client.post(
        "/api/mcp/invoke",
        json={"project_id": "general", "tool_name": "system.echo", "arguments": {"message": "verified"}},
    )
    assert response.status_code == 200
    assert response.json()["result"]["content"][0]["text"] == "verified"


def test_external_mcp_http_and_stdio_connectors(client: TestClient) -> None:
    with _HTTPMCPServer() as server:
        created = client.post(
            "/api/mcp/connectors",
            json={
                "name": "HTTP test",
                "transport": "http",
                "endpoint": server.endpoint,
                "enabled": True,
                "allowed_tools": ["external.echo"],
                "timeout_seconds": 2,
            },
        )
        assert created.status_code == 201
        http_id = created.json()["id"]
        discovered = client.post(f"/api/mcp/connectors/{http_id}/discover")
        assert discovered.status_code == 200
        assert discovered.json()["tools"][0]["name"] == "external.echo"
        invoked = client.post(
            "/api/mcp/invoke",
            json={
                "project_id": "general",
                "connector_id": http_id,
                "tool_name": "external.echo",
                "arguments": {"message": "verified"},
            },
        )
        assert invoked.status_code == 200
        assert invoked.json()["result"]["content"][0]["text"] == "http:verified"

    stdio = client.post(
        "/api/mcp/connectors",
        json={
            "name": "stdio test",
            "transport": "stdio",
            "command": "test-stdio",
            "enabled": True,
            "allowed_tools": ["external.echo"],
            "timeout_seconds": 3,
        },
    )
    assert stdio.status_code == 201
    stdio_id = stdio.json()["id"]
    assert client.post(f"/api/mcp/connectors/{stdio_id}/discover").status_code == 200
    stdio_call = client.post(
        "/api/mcp/invoke",
        json={
            "project_id": "general",
            "connector_id": stdio_id,
            "tool_name": "external.echo",
            "arguments": {"message": "verified"},
        },
    )
    assert stdio_call.status_code == 200
    assert stdio_call.json()["result"]["content"][0]["text"] == "stdio:verified"

    disabled = client.patch(f"/api/mcp/connectors/{stdio_id}", json={"enabled": False})
    assert disabled.json()["connection_status"] == "disabled"
    assert stdio_call.status_code == 200
    blocked = client.post(
        "/api/mcp/invoke",
        json={
            "project_id": "general",
            "connector_id": stdio_id,
            "tool_name": "external.echo",
            "arguments": {},
        },
    )
    assert blocked.status_code == 400


def test_external_mcp_is_fail_closed_and_failure_isolated(client: TestClient) -> None:
    unknown_command = client.post(
        "/api/mcp/connectors",
        json={
            "name": "unsafe",
            "transport": "stdio",
            "command": "not-allowlisted",
            "enabled": True,
        },
    )
    assert unknown_command.status_code == 400

    unavailable = client.post(
        "/api/mcp/connectors",
        json={
            "name": "unavailable",
            "transport": "http",
            "endpoint": "http://127.0.0.1:1/mcp",
            "enabled": True,
            "timeout_seconds": 0.2,
        },
    ).json()
    failed = client.post(f"/api/mcp/connectors/{unavailable['id']}/discover")
    assert failed.status_code == 502
    persisted = client.get("/api/mcp/connectors").json()["items"]
    item = next(value for value in persisted if value["id"] == unavailable["id"])
    assert item["connection_status"] == "error"
    assert item["last_error"]
    assert client.get("/health").status_code == 200


@pytest.mark.asyncio
async def test_mcp_reference_server_uses_stateless_json_rpc() -> None:
    server = EchoMCPServer()
    response = await server.request(
        {
            "jsonrpc": "2.0",
            "id": "discover-1",
            "method": "server/discover",
            "params": {"_meta": {"io.modelcontextprotocol/clientInfo": {"name": "test", "version": "1"}}},
        }
    )
    assert response["result"]["protocolVersion"] == "2026-07-28"
    listed = await server.request(
        {"jsonrpc": "2.0", "id": "list-1", "method": "tools/list", "params": {}}
    )
    assert listed["result"]["tools"][0]["inputSchema"]["required"] == ["message"]


def test_chat_stream_tool_trace_and_provider_switch(client: TestClient) -> None:
    first = client.post(
        "/api/chat/stream",
        json={
            "provider": "openai",
            "model": "openai-test",
            "project_id": "general",
            "content": "Use the test tool.",
            "tool": {"name": "system.echo", "arguments": {"message": "tool-ok"}},
        },
    )
    assert first.status_code == 200
    assert "event: tool_start" in first.text
    assert "event: tool_result" in first.text
    assert "event: done" in first.text
    first_events = _sse_data(first.text)
    conversation_id = first_events[-1]["payload"]["conversation_id"]

    second = client.post(
        "/api/chat/stream",
        json={
            "conversation_id": conversation_id,
            "provider": "anthropic",
            "model": "anthropic-test",
            "project_id": "general",
            "content": "Continue with the other provider.",
        },
    )
    assert second.status_code == 200
    assert "from anthropic/anthropic-test" in second.text
    messages = client.get(f"/api/conversations/{conversation_id}/messages").json()["items"]
    assert [message["role"] for message in messages] == ["user", "assistant", "user", "assistant"]


def test_conversation_filter_detail_trace_and_restart(runtime_factory) -> None:
    first_runtime = runtime_factory()
    with TestClient(create_app(runtime=first_runtime)) as first:
        conversation = first.post(
            "/api/conversations",
            json={
                "provider": "openai",
                "model": "openai-test",
                "project_id": "general",
                "title": "New conversation",
            },
        ).json()
        other = first.post(
            "/api/conversations",
            json={
                "provider": "openai",
                "model": "openai-test",
                "project_id": "soccer",
                "title": "Soccer plugin conversation",
            },
        ).json()
        streamed = first.post(
            "/api/chat/stream",
            json={
                "conversation_id": conversation["id"],
                "provider": "openai",
                "model": "openai-test",
                "project_id": "general",
                "content": "Persist this exchange.",
                "tool": {"name": "system.echo", "arguments": {"message": "persisted-tool"}},
            },
        )
        assert streamed.status_code == 200
        filtered = first.get("/api/conversations?project_id=general").json()["items"]
        assert [item["id"] for item in filtered] == [conversation["id"]]
        assert other["id"] not in {item["id"] for item in filtered}
        detail = first.get(f"/api/conversations/{conversation['id']}").json()
        assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
        assert {event["type"] for event in detail["execution_events"]} >= {
            "tool_start",
            "tool_result",
            "message",
            "done",
        }

    restarted_runtime = runtime_factory()
    with TestClient(create_app(runtime=restarted_runtime)) as restarted:
        restored = restarted.get(f"/api/conversations/{conversation['id']}")
        assert restored.status_code == 200
        restored_body = restored.json()
        prior_event_count = len(restored_body["execution_events"])
        continued = restarted.post(
            "/api/chat/stream",
            json={
                "conversation_id": conversation["id"],
                "provider": "anthropic",
                "model": "anthropic-test",
                "project_id": "general",
                "content": "Continue after restart.",
            },
        )
        assert continued.status_code == 200
        final = restarted.get(f"/api/conversations/{conversation['id']}").json()
        assert [message["role"] for message in final["messages"]] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        assert len(final["execution_events"]) > prior_event_count
        assert final["conversation"]["provider"] == "anthropic"


def test_general_full_external_tool_chain_restores_after_restart(runtime_factory) -> None:
    first_runtime = runtime_factory()
    with TestClient(create_app(runtime=first_runtime)) as first:
        connector = first.post(
            "/api/mcp/connectors",
            json={
                "name": "General stdio",
                "transport": "stdio",
                "command": "test-stdio",
                "enabled": True,
                "allowed_tools": ["external.echo"],
                "timeout_seconds": 3,
            },
        ).json()
        response = first.post(
            "/api/chat/stream",
            json={
                "provider": "openai",
                "model": "openai-test",
                "project_id": "general",
                "content": "Use the external echo tool with first-pass.",
                "tool": {
                    "connector_id": connector["id"],
                    "name": "external.echo",
                    "arguments": {"message": "first-pass"},
                },
            },
        )
        assert response.status_code == 200
        events = _sse_data(response.text)
        assert [item["type"] for item in events] == [
            "tool_start",
            "tool_result",
            "message",
            "message",
            "done",
        ]
        assert events[0]["payload"]["provider_tool_call_id"] == "openai-tool-call"
        assert events[1]["payload"]["result"]["content"][0]["text"] == "stdio:first-pass"
        conversation_id = events[-1]["payload"]["conversation_id"]
        assert first.post(
            "/api/mcp/invoke",
            json={
                "project_id": "soccer",
                "connector_id": connector["id"],
                "tool_name": "external.echo",
                "arguments": {"message": "blocked"},
            },
        ).status_code == 400

    restarted_runtime = runtime_factory()
    with TestClient(create_app(runtime=restarted_runtime)) as restarted:
        restored = restarted.get(f"/api/conversations/{conversation_id}").json()
        assert len(restored["messages"]) == 2
        assert restored["execution_events"][1]["payload"]["result"]["content"][0]["text"] == "stdio:first-pass"
        continued = restarted.post(
            "/api/chat/stream",
            json={
                "conversation_id": conversation_id,
                "provider": "anthropic",
                "model": "anthropic-test",
                "project_id": "general",
                "content": "Continue with second-pass.",
                "tool": {
                    "connector_id": connector["id"],
                    "name": "external.echo",
                    "arguments": {"message": "second-pass"},
                },
            },
        )
        assert continued.status_code == 200
        continued_events = _sse_data(continued.text)
        assert continued_events[0]["payload"]["provider_tool_call_id"] == "anthropic-tool-call"
        assert continued_events[1]["payload"]["result"]["content"][0]["text"] == "stdio:second-pass"
        final = restarted.get(f"/api/conversations/{conversation_id}").json()
        assert [item["role"] for item in final["messages"]] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        assert len(final["execution_events"]) == 10
        assert final["conversation"]["project_id"] == "general"


@pytest.mark.asyncio
async def test_chat_cancellation_is_normalized_without_assistant_message(runtime) -> None:
    runtime.database.migrate()

    async def disconnected() -> bool:
        return True

    output = "".join(
        [
            item
            async for item in stream_chat(
                runtime,
                ChatRequest(
                    provider="openai",
                    model="openai-test",
                    project_id="general",
                    content="Cancel this stream.",
                ),
                disconnected,
            )
        ]
    )
    events = _sse_data(output)
    assert events[0]["type"] == "error"
    assert events[0]["payload"]["code"] == "cancelled"
    conversation_id = events[-1]["payload"]["conversation_id"]
    assert [item.role.value for item in runtime.database.list_messages(conversation_id)] == [
        "user"
    ]
