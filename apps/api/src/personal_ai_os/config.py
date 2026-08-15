from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from personal_ai_os_core import DeploymentMode, PlanId


DEFAULT_REALTIME_ENDPOINT = "https://api.openai.com/v1/realtime/calls"


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"Expected a boolean value, received {value!r}")


def _stdio_commands(value: str) -> dict[str, tuple[str, ...]]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError("PERSONAL_AI_OS_MCP_STDIO_COMMANDS must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("PERSONAL_AI_OS_MCP_STDIO_COMMANDS must be a JSON object")
    commands: dict[str, tuple[str, ...]] = {}
    for alias, argv in parsed.items():
        if not isinstance(alias, str) or not alias or not isinstance(argv, list) or not argv:
            raise RuntimeError("Each stdio MCP command must map a non-empty alias to an argv array")
        if not all(isinstance(item, str) and item for item in argv):
            raise RuntimeError("stdio MCP argv entries must be non-empty strings")
        if not Path(argv[0]).is_absolute():
            raise RuntimeError("stdio MCP executables must use absolute paths")
        commands[alias] = tuple(argv)
    return commands


def _realtime_endpoint(value: str) -> str:
    parsed = urlsplit(value.strip())
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not parsed.path.rstrip("/").endswith("/realtime/calls")
    ):
        raise RuntimeError(
            "PERSONAL_AI_OS_REALTIME_ENDPOINT must be an HTTPS calls endpoint ending in /realtime/calls"
        )
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    cors_origins: tuple[str, ...]
    openai_models: tuple[str, ...]
    anthropic_models: tuple[str, ...]
    github_models_models: tuple[str, ...]
    default_provider: str
    default_model: str
    openai_api_key: str | None = field(default=None, repr=False)
    anthropic_api_key: str | None = field(default=None, repr=False)
    github_models_token: str | None = field(default=None, repr=False)
    realtime_api_key: str | None = field(default=None, repr=False)
    realtime_endpoint: str = DEFAULT_REALTIME_ENDPOINT
    mcp_stdio_commands: dict[str, tuple[str, ...]] = field(default_factory=dict, repr=False)
    provider_timeout_seconds: float = 90
    provider_max_retries: int = 2
    provider_retry_base_seconds: float = 0.25
    realtime_model: str = "gpt-realtime-2.1"
    realtime_voice: str = "marin"
    realtime_transcription_model: str = "gpt-realtime-whisper"
    auth_required: bool = False
    access_password: str | None = field(default=None, repr=False)
    session_secret: str | None = field(default=None, repr=False)
    access_session_hours: int = 168
    deployment_mode: DeploymentMode = DeploymentMode.COMMUNITY
    plan: PlanId = PlanId.COMMUNITY
    tenant_id: str = "local"
    actor_id: str = "local-owner"
    cloud_accounts_ready: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("PERSONAL_AI_OS_DATA_DIR", "./data")).resolve()
        auth_required = _bool(os.getenv("PERSONAL_AI_OS_REQUIRE_AUTH", "false"))
        access_password = os.getenv("PERSONAL_AI_OS_ACCESS_PASSWORD") or None
        session_secret = os.getenv("PERSONAL_AI_OS_SESSION_SECRET") or None
        if auth_required and not access_password:
            raise RuntimeError(
                "PERSONAL_AI_OS_ACCESS_PASSWORD is required when access protection is enabled"
            )
        if auth_required and len(access_password) < 10:
            raise RuntimeError(
                "PERSONAL_AI_OS_ACCESS_PASSWORD must contain at least 10 characters"
            )
        if auth_required and (not session_secret or len(session_secret) < 32):
            raise RuntimeError(
                "PERSONAL_AI_OS_SESSION_SECRET must contain at least 32 characters when access protection is enabled"
            )
        deployment_mode = DeploymentMode(
            os.getenv("PERSONAL_AI_OS_DEPLOYMENT_MODE", DeploymentMode.COMMUNITY.value)
        )
        default_plan = (
            PlanId.COMMUNITY.value
            if deployment_mode is DeploymentMode.COMMUNITY
            else PlanId.CLOUD_FREE.value
        )
        plan = PlanId(os.getenv("PERSONAL_AI_OS_PLAN", default_plan))
        tenant_id = os.getenv("PERSONAL_AI_OS_TENANT_ID", "local").strip()
        actor_id = os.getenv("PERSONAL_AI_OS_ACTOR_ID", "local-owner").strip()
        if not tenant_id or not actor_id:
            raise RuntimeError("Tenant and actor identifiers must not be blank")
        if deployment_mode is DeploymentMode.COMMUNITY and plan is not PlanId.COMMUNITY:
            raise RuntimeError("Community deployment must use the community plan")
        if deployment_mode is DeploymentMode.CLOUD and plan is PlanId.COMMUNITY:
            raise RuntimeError("Cloud deployment must use a cloud plan")
        return cls(
            data_dir=data_dir,
            cors_origins=_csv(os.getenv("PERSONAL_AI_OS_CORS_ORIGINS", "http://localhost:3000")),
            openai_models=_csv(os.getenv("PERSONAL_AI_OS_OPENAI_MODELS", "gpt-5.1,gpt-4.1-mini")),
            anthropic_models=_csv(
                os.getenv("PERSONAL_AI_OS_ANTHROPIC_MODELS", "claude-sonnet-4-5,claude-haiku-4-5")
            ),
            github_models_models=_csv(
                os.getenv("PERSONAL_AI_OS_GITHUB_MODELS_MODELS", "openai/gpt-4.1")
            ),
            default_provider=os.getenv("PERSONAL_AI_OS_DEFAULT_PROVIDER", "openai"),
            default_model=os.getenv("PERSONAL_AI_OS_DEFAULT_MODEL", "gpt-5.1"),
            openai_api_key=os.getenv("PERSONAL_AI_OS_OPENAI_API_KEY") or None,
            anthropic_api_key=os.getenv("PERSONAL_AI_OS_ANTHROPIC_API_KEY") or None,
            github_models_token=os.getenv("PERSONAL_AI_OS_GITHUB_MODELS_TOKEN") or None,
            realtime_api_key=os.getenv("PERSONAL_AI_OS_REALTIME_API_KEY") or None,
            realtime_endpoint=_realtime_endpoint(
                os.getenv("PERSONAL_AI_OS_REALTIME_ENDPOINT")
                or DEFAULT_REALTIME_ENDPOINT
            ),
            mcp_stdio_commands=_stdio_commands(
                os.getenv("PERSONAL_AI_OS_MCP_STDIO_COMMANDS", "{}")
            ),
            provider_timeout_seconds=float(
                os.getenv("PERSONAL_AI_OS_PROVIDER_TIMEOUT_SECONDS", "90")
            ),
            provider_max_retries=max(
                0, int(os.getenv("PERSONAL_AI_OS_PROVIDER_MAX_RETRIES", "2"))
            ),
            provider_retry_base_seconds=max(
                0, float(os.getenv("PERSONAL_AI_OS_PROVIDER_RETRY_BASE_SECONDS", "0.25"))
            ),
            realtime_model=os.getenv(
                "PERSONAL_AI_OS_REALTIME_MODEL", "gpt-realtime-2.1"
            ),
            realtime_voice=os.getenv("PERSONAL_AI_OS_REALTIME_VOICE", "marin"),
            realtime_transcription_model=os.getenv(
                "PERSONAL_AI_OS_REALTIME_TRANSCRIPTION_MODEL", "gpt-realtime-whisper"
            ),
            auth_required=auth_required,
            access_password=access_password,
            session_secret=session_secret,
            access_session_hours=max(
                1, min(24 * 30, int(os.getenv("PERSONAL_AI_OS_ACCESS_SESSION_HOURS", "168")))
            ),
            deployment_mode=deployment_mode,
            plan=plan,
            tenant_id=tenant_id,
            actor_id=actor_id,
        )

    def validate_for_startup(self) -> None:
        if self.deployment_mode is DeploymentMode.CLOUD and not self.cloud_accounts_ready:
            raise RuntimeError(
                "Cloud mode is not available until the account identity service is configured"
            )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "personal_ai_os.db"

    @property
    def realtime_key(self) -> str | None:
        if self.realtime_provider == "compatible":
            return self.realtime_api_key
        return self.realtime_api_key or self.openai_api_key

    @property
    def realtime_provider(self) -> str:
        return "openai" if self.realtime_endpoint == DEFAULT_REALTIME_ENDPOINT else "compatible"
