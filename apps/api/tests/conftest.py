from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient
from personal_ai_os_core import Message
from personal_ai_os_mcp import ConnectorRegistry, EchoMCPServer, MCPGateway
from personal_ai_os_projects import P5Project, create_project_registry
from personal_ai_os_providers import ProviderRegistry, ProviderTool, ProviderToolCall

from personal_ai_os.config import Settings
from personal_ai_os.db import Database
from personal_ai_os.main import create_app
from personal_ai_os.mcp_service import ExternalMCPService
from personal_ai_os.runtime import Runtime
from personal_ai_os.p5_mcp import P5MCPServer


class FakeProvider:
    def __init__(self, provider_id: str, models: tuple[str, ...]) -> None:
        self.id = provider_id
        self.models = models

    @property
    def configured(self) -> bool:
        return True

    def describe(self) -> dict[str, object]:
        return {"id": self.id, "configured": True, "models": list(self.models)}

    async def stream(self, messages: list[Message], model: str) -> AsyncIterator[str]:
        assert messages[-1].content
        yield "hello "
        yield f"from {self.id}/{model}"

    async def request_tool(
        self, messages: list[Message], model: str, tool: ProviderTool
    ) -> ProviderToolCall:
        assert messages[-1].content
        return ProviderToolCall(
            id=f"{self.id}-tool-call",
            name=tool.name,
            arguments=tool.suggested_arguments or {},
        )

    async def stream_after_tool(
        self,
        messages: list[Message],
        model: str,
        call: ProviderToolCall,
        result: dict[str, Any],
    ) -> AsyncIterator[str]:
        assert call.name
        assert result
        async for chunk in self.stream(messages, model):
            yield chunk


@pytest.fixture
def runtime_factory(tmp_path: Path):
    def create() -> Runtime:
        settings = Settings(
            data_dir=tmp_path,
            cors_origins=("http://localhost:3000",),
            openai_models=("openai-test",),
            anthropic_models=("anthropic-test",),
            default_provider="openai",
            default_model="openai-test",
            mcp_stdio_commands={
                "test-stdio": (
                    sys.executable,
                    str(Path(__file__).parent / "fixtures" / "stdio_mcp_server.py"),
                )
            },
        )
        projects = create_project_registry(data_dir=tmp_path)
        database = Database(settings.database_path)
        providers = ProviderRegistry(
            [
                FakeProvider("openai", ("openai-test",)),
                FakeProvider("anthropic", ("anthropic-test",)),
            ]
        )
        p5_project = projects.get("p5")
        assert isinstance(p5_project, P5Project)
        return Runtime(
            settings=settings,
            database=database,
            providers=providers,
            projects=projects,
            mcp=MCPGateway(projects, [EchoMCPServer(), P5MCPServer(p5_project)]),
            external_mcp=ExternalMCPService(
                database, projects, ConnectorRegistry(settings.mcp_stdio_commands)
            ),
        )

    return create


@pytest.fixture
def runtime(runtime_factory) -> Runtime:
    return runtime_factory()


@pytest.fixture
def client(runtime: Runtime) -> TestClient:
    with TestClient(create_app(runtime=runtime)) as test_client:
        yield test_client
