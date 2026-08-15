from __future__ import annotations

import httpx

from .openai import OpenAIAdapter


GITHUB_MODELS_ENDPOINT = "https://models.github.ai/inference/chat/completions"
GITHUB_API_VERSION = "2026-03-10"


class GitHubModelsAdapter(OpenAIAdapter):
    """GitHub Models inference through the OpenAI-compatible chat-completions protocol."""

    id = "github_models"
    provider_name = "GitHub Models"

    def __init__(
        self,
        token: str | None,
        models: tuple[str, ...],
        timeout_seconds: float = 90,
        max_retries: int = 2,
        retry_base_seconds: float = 0.25,
        *,
        endpoint: str = GITHUB_MODELS_ENDPOINT,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(
            token,
            models,
            timeout_seconds,
            max_retries,
            retry_base_seconds,
            endpoint=endpoint,
            transport=transport,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "Content-Type": "application/json",
        }
