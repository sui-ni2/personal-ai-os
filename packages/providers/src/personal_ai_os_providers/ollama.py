from __future__ import annotations

import httpx

from .base import ProviderNotConfigured, validate_model
from .openai import OpenAIAdapter


DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434/v1/chat/completions"


class OllamaAdapter(OpenAIAdapter):
    """Local Ollama inference through its OpenAI-compatible chat-completions API."""

    id = "ollama"
    provider_name = "Ollama"

    def __init__(
        self,
        enabled: bool,
        models: tuple[str, ...],
        timeout_seconds: float = 90,
        max_retries: int = 2,
        retry_base_seconds: float = 0.25,
        *,
        endpoint: str = DEFAULT_OLLAMA_ENDPOINT,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._enabled = enabled
        super().__init__(
            "ollama",
            models,
            timeout_seconds,
            max_retries,
            retry_base_seconds,
            endpoint=endpoint,
            transport=transport,
        )

    @property
    def configured(self) -> bool:
        return self._enabled

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def _validate(self, model: str) -> None:
        if not self._enabled:
            raise ProviderNotConfigured("Ollama is not enabled on the server")
        validate_model(model, self.models)
