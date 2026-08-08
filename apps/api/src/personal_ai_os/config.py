from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


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
        )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "personal_ai_os.db"
