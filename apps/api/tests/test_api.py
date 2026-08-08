from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from personal_ai_os_mcp import EchoMCPServer


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
