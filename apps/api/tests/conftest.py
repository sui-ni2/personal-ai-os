from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from personal_ai_os_core import Message
from personal_ai_os_mcp import EchoMCPServer, MCPGateway
from personal_ai_os_projects import create_project_registry
from personal_ai_os_providers import ProviderRegistry

from personal_ai_os.config import Settings
from personal_ai_os.db import Database
from personal_ai_os.main import create_app
from personal_ai_os.runtime import Runtime


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


@pytest.fixture
def runtime(tmp_path: Path) -> Runtime:
    settings = Settings(
        data_dir=tmp_path,
        cors_origins=("http://localhost:3000",),
        openai_models=("openai-test",),
        anthropic_models=("anthropic-test",),
        default_provider="openai",
        default_model="openai-test",
    )
    projects = create_project_registry()
    database = Database(settings.database_path)
    providers = ProviderRegistry(
        [FakeProvider("openai", ("openai-test",)), FakeProvider("anthropic", ("anthropic-test",))]
    )
    return Runtime(
        settings=settings,
        database=database,
        providers=providers,
        projects=projects,
        mcp=MCPGateway(projects, [EchoMCPServer()]),
    )


@pytest.fixture
def client(runtime: Runtime) -> TestClient:
    with TestClient(create_app(runtime=runtime)) as test_client:
        yield test_client
