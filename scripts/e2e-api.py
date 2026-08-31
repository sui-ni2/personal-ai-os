"""Deterministic local API fixture for browser E2E; never loaded by production startup."""

from __future__ import annotations

import argparse
import json
from collections.abc import AsyncIterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import uvicorn
from personal_ai_os_core import Message
from personal_ai_os_providers import ProviderError, ProviderRegistry, ProviderTool, ProviderToolCall

from personal_ai_os.config import Settings
from personal_ai_os.main import create_app
from personal_ai_os.runtime import create_runtime


class E2EProvider:
    def __init__(self, provider_id: str, model: str) -> None:
        self.id = provider_id
        self.models = (model,)

    @property
    def configured(self) -> bool:
        return True

    def describe(self) -> dict[str, object]:
        return {"id": self.id, "configured": True, "models": list(self.models)}

    async def stream(self, messages: list[Message], model: str) -> AsyncIterator[str]:
        assert model in self.models
        assert messages[-1].content
        if self.id == "openai" and "force deterministic timeout" in messages[-1].content:
            raise ProviderError("Deterministic timeout", code="timeout", status_code=408, retryable=True)
        yield f"Deterministic E2E response from {self.id}"

    async def request_tool(
        self, messages: list[Message], model: str, tool: ProviderTool
    ) -> ProviderToolCall:
        assert model in self.models
        assert messages[-1].content
        return ProviderToolCall(id="e2e-tool", name=tool.name, arguments=tool.suggested_arguments or {})

    async def stream_after_tool(
        self,
        messages: list[Message],
        model: str,
        call: ProviderToolCall,
        result: dict[str, object],
    ) -> AsyncIterator[str]:
        assert call.name and result
        async for chunk in self.stream(messages, model):
            yield chunk


class _ExternalToolHandler(BaseHTTPRequestHandler):
    """Tiny local-only MCP fixture used to exercise confirmation in the browser."""

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        request = json.loads(self.rfile.read(length))
        method = request.get("method")
        if method == "tools/list":
            result: dict[str, object] = {
                "tools": [{
                    "name": "external.echo",
                    "description": "Deterministic external side effect fixture.",
                    "inputSchema": {"type": "object", "properties": {"message": {"type": "string"}}},
                }]
            }
        elif method == "tools/call":
            result = {"content": [{"type": "text", "text": "deterministic external fixture completed"}]}
        else:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"jsonrpc": "2.0", "id": request.get("id"), "result": result}).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class E2EExternalToolServer:
    def __init__(self) -> None:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _ExternalToolHandler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)

    @property
    def endpoint(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/mcp"

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    settings = Settings(
        data_dir=args.data_dir.resolve(),
        cors_origins=("http://127.0.0.1:3000",),
        openai_models=("openai-e2e",),
        anthropic_models=("anthropic-e2e",),
        default_provider="openai",
        default_model="openai-e2e",
    )
    tool_server = E2EExternalToolServer()
    tool_server.start()
    runtime = create_runtime(settings)
    runtime.database.migrate()
    runtime.providers = ProviderRegistry([
        E2EProvider("openai", "openai-e2e"),
        E2EProvider("anthropic", "anthropic-e2e"),
    ])
    runtime.external_mcp.create({
        "name": "Deterministic external confirmation",
        "transport": "http",
        "endpoint": tool_server.endpoint,
        "enabled": True,
        "allowed_tools": ["external.echo"],
    })
    try:
        uvicorn.run(create_app(runtime=runtime), host="127.0.0.1", port=args.port, log_level="warning")
    finally:
        tool_server.close()


if __name__ == "__main__":
    main()
