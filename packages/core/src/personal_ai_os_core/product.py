from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class DeploymentMode(StrEnum):
    COMMUNITY = "community"
    CLOUD = "cloud"


class PlanId(StrEnum):
    COMMUNITY = "community"
    CLOUD_FREE = "cloud_free"
    CLOUD_PERSONAL = "cloud_personal"
    CLOUD_PRO = "cloud_pro"


class Capability(StrEnum):
    CHAT = "chat"
    PROJECTS = "projects"
    FILES = "files"
    TASKS = "tasks"
    ARTIFACTS = "artifacts"
    MEMORY = "memory"
    LOCAL_MODELS = "local_models"
    MANAGED_MODELS = "managed_models"
    CUSTOM_PROVIDERS = "custom_providers"
    MCP = "mcp"
    PLUGINS = "plugins"
    DEVICE_SYNC = "device_sync"
    MANAGED_BACKUP = "managed_backup"
    USAGE_CONTROLS = "usage_controls"
    ADVANCED_SETTINGS = "advanced_settings"


COMMUNITY_CAPABILITIES = frozenset(
    {
        Capability.CHAT,
        Capability.PROJECTS,
        Capability.FILES,
        Capability.TASKS,
        Capability.ARTIFACTS,
        Capability.MEMORY,
        Capability.LOCAL_MODELS,
        Capability.CUSTOM_PROVIDERS,
        Capability.MCP,
        Capability.PLUGINS,
        Capability.USAGE_CONTROLS,
        Capability.ADVANCED_SETTINGS,
    }
)

CLOUD_PLAN_CAPABILITIES: dict[PlanId, frozenset[Capability]] = {
    PlanId.CLOUD_FREE: frozenset(
        {
            Capability.CHAT,
            Capability.PROJECTS,
            Capability.FILES,
            Capability.TASKS,
            Capability.ARTIFACTS,
            Capability.MEMORY,
            Capability.MANAGED_MODELS,
            Capability.DEVICE_SYNC,
            Capability.MANAGED_BACKUP,
            Capability.USAGE_CONTROLS,
        }
    ),
    PlanId.CLOUD_PERSONAL: frozenset(
        {
            Capability.CHAT,
            Capability.PROJECTS,
            Capability.FILES,
            Capability.TASKS,
            Capability.ARTIFACTS,
            Capability.MEMORY,
            Capability.MANAGED_MODELS,
            Capability.CUSTOM_PROVIDERS,
            Capability.DEVICE_SYNC,
            Capability.MANAGED_BACKUP,
            Capability.USAGE_CONTROLS,
        }
    ),
    PlanId.CLOUD_PRO: frozenset(Capability),
}


class ProductProfile(BaseModel):
    product_name: str = "Personal AI OS"
    value_proposition: str = (
        "A user-controlled AI workspace that remembers context, completes work, "
        "and preserves reusable outcomes."
    )
    target_user: str = (
        "People managing long-running projects across files, conversations, and devices."
    )
    deployment_mode: DeploymentMode
    plan: PlanId
    tenant_id: str = Field(min_length=1, max_length=120)
    actor_id: str = Field(min_length=1, max_length=120)
    capabilities: list[Capability]
    cloud_accounts_ready: bool

    def allows(self, capability: Capability) -> bool:
        return capability in self.capabilities


def build_product_profile(
    deployment_mode: DeploymentMode,
    plan: PlanId,
    tenant_id: str,
    actor_id: str,
    *,
    cloud_accounts_ready: bool = False,
) -> ProductProfile:
    if deployment_mode is DeploymentMode.COMMUNITY:
        if plan is not PlanId.COMMUNITY:
            raise ValueError("Community deployment must use the community plan")
        capabilities = COMMUNITY_CAPABILITIES
    else:
        if plan is PlanId.COMMUNITY:
            raise ValueError("Cloud deployment must use a cloud plan")
        capabilities = CLOUD_PLAN_CAPABILITIES[plan]
    return ProductProfile(
        deployment_mode=deployment_mode,
        plan=plan,
        tenant_id=tenant_id,
        actor_id=actor_id,
        capabilities=sorted(capabilities, key=lambda item: item.value),
        cloud_accounts_ready=cloud_accounts_ready,
    )
