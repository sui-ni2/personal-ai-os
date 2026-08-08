from __future__ import annotations

from dataclasses import dataclass

from personal_ai_os_core import ProjectRegistry
from personal_ai_os_mcp import EchoMCPServer, MCPGateway
from personal_ai_os_projects import create_project_registry
from personal_ai_os_providers import AnthropicAdapter, OpenAIAdapter, ProviderRegistry

from .config import Settings
from .db import Database


@dataclass
class Runtime:
    settings: Settings
    database: Database
    providers: ProviderRegistry
    projects: ProjectRegistry
    mcp: MCPGateway


def create_runtime(settings: Settings) -> Runtime:
    projects = create_project_registry()
    providers = ProviderRegistry(
        [
            OpenAIAdapter(settings.openai_api_key, settings.openai_models),
            AnthropicAdapter(settings.anthropic_api_key, settings.anthropic_models),
        ]
    )
    database = Database(settings.database_path)
    return Runtime(
        settings=settings,
        database=database,
        providers=providers,
        projects=projects,
        mcp=MCPGateway(projects=projects, servers=[EchoMCPServer()]),
    )
