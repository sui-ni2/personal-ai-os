from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from pathlib import Path


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


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


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    cors_origins: tuple[str, ...]
    openai_models: tuple[str, ...]
    anthropic_models: tuple[str, ...]
    default_provider: str
    default_model: str
    openai_api_key: str | None = field(default=None, repr=False)
    anthropic_api_key: str | None = field(default=None, repr=False)
    mcp_stdio_commands: dict[str, tuple[str, ...]] = field(default_factory=dict, repr=False)
    provider_timeout_seconds: float = 90
    provider_max_retries: int = 2
    provider_retry_base_seconds: float = 0.25
    realtime_model: str = "gpt-realtime-2.1"
    realtime_voice: str = "marin"
    realtime_transcription_model: str = "gpt-live-transcribe"

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("PERSONAL_AI_OS_DATA_DIR", "./data")).resolve()
        return cls(
            data_dir=data_dir,
            cors_origins=_csv(os.getenv("PERSONAL_AI_OS_CORS_ORIGINS", "http://localhost:3000")),
            openai_models=_csv(os.getenv("PERSONAL_AI_OS_OPENAI_MODELS", "gpt-5.1,gpt-4.1-mini")),
            anthropic_models=_csv(
                os.getenv("PERSONAL_AI_OS_ANTHROPIC_MODELS", "claude-sonnet-4-5,claude-haiku-4-5")
            ),
            default_provider=os.getenv("PERSONAL_AI_OS_DEFAULT_PROVIDER", "openai"),
            default_model=os.getenv("PERSONAL_AI_OS_DEFAULT_MODEL", "gpt-5.1"),
            openai_api_key=os.getenv("PERSONAL_AI_OS_OPENAI_API_KEY") or None,
            anthropic_api_key=os.getenv("PERSONAL_AI_OS_ANTHROPIC_API_KEY") or None,
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
                "PERSONAL_AI_OS_REALTIME_TRANSCRIPTION_MODEL", "gpt-live-transcribe"
            ),
        )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "personal_ai_os.db"
