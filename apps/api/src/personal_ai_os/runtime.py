from __future__ import annotations

from dataclasses import dataclass

from personal_ai_os_core import ProductProfile, ProjectRegistry, build_product_profile
from personal_ai_os_mcp import ConnectorRegistry, EchoMCPServer, MCPGateway
from personal_ai_os_projects import create_project_registry
from personal_ai_os_projects import P5Project
from personal_ai_os_providers import AnthropicAdapter, OpenAIAdapter, ProviderRegistry

from .config import Settings
from .db import Database
from .mcp_service import ExternalMCPService
from .p5_mcp import P5MCPServer


@dataclass
class Runtime:
    settings: Settings
    database: Database
    providers: ProviderRegistry
    projects: ProjectRegistry
    mcp: MCPGateway
    external_mcp: ExternalMCPService
    product: ProductProfile


def create_runtime(settings: Settings) -> Runtime:
    settings.validate_for_startup()
    product = build_product_profile(
        settings.deployment_mode,
        settings.plan,
        settings.tenant_id,
        settings.actor_id,
        cloud_accounts_ready=settings.cloud_accounts_ready,
    )
    projects = create_project_registry(data_dir=settings.data_dir)
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
    database = Database(
        settings.database_path,
        tenant_id=settings.tenant_id,
        actor_id=settings.actor_id,
        deployment_mode=settings.deployment_mode.value,
    )
    connector_registry = ConnectorRegistry(settings.mcp_stdio_commands)
    p5_project = projects.get("p5")
    if not isinstance(p5_project, P5Project):
        raise RuntimeError("P5 project registry entry is invalid")
    return Runtime(
        settings=settings,
        database=database,
        providers=providers,
        projects=projects,
        mcp=MCPGateway(projects=projects, servers=[EchoMCPServer(), P5MCPServer(p5_project)]),
        external_mcp=ExternalMCPService(database, projects, connector_registry),
        product=product,
    )
