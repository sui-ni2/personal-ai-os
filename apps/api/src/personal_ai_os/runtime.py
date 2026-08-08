from __future__ import annotations

from dataclasses import dataclass

from personal_ai_os_core import ProjectRegistry
from personal_ai_os_mcp import ConnectorRegistry, EchoMCPServer, MCPGateway
from personal_ai_os_projects import create_project_registry
from personal_ai_os_providers import AnthropicAdapter, OpenAIAdapter, ProviderRegistry

from .config import Settings
from .db import Database
from .mcp_service import ExternalMCPService


@dataclass
class Runtime:
    settings: Settings
    database: Database
    providers: ProviderRegistry
    projects: ProjectRegistry
    mcp: MCPGateway
    external_mcp: ExternalMCPService


def create_runtime(settings: Settings) -> Runtime:
    projects = create_project_registry()
    providers = ProviderRegistry(
        [
            OpenAIAdapter(
                settings.openai_api_key,
                settings.openai_models,
                settings.provider_timeout_seconds,
                settings.provider_max_retries,
                settings.provider_retry_base_seconds,
            ),
            AnthropicAdapter(
                settings.anthropic_api_key,
                settings.anthropic_models,
                settings.provider_timeout_seconds,
                settings.provider_max_retries,
                settings.provider_retry_base_seconds,
            ),
        ]
    )
    database = Database(settings.database_path)
    connector_registry = ConnectorRegistry(settings.mcp_stdio_commands)
    return Runtime(
        settings=settings,
        database=database,
        providers=providers,
        projects=projects,
        mcp=MCPGateway(projects=projects, servers=[EchoMCPServer()]),
        external_mcp=ExternalMCPService(database, projects, connector_registry),
    )
