from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

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
        max_output_tokens: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._enabled = enabled
        self._max_output_tokens = max_output_tokens
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

    def _bounded_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._max_output_tokens is None:
            return payload
        bounded = dict(payload)
        bounded.setdefault("max_tokens", self._max_output_tokens)
        return bounded

    async def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await super()._post_json(self._bounded_payload(payload))

    async def _stream_payload(self, payload: dict[str, Any]) -> AsyncIterator[str]:
        async for chunk in super()._stream_payload(self._bounded_payload(payload)):
            yield chunk

    def _validate(self, model: str) -> None:
        if not self._enabled:
            raise ProviderNotConfigured("Ollama is not enabled on the server")
        validate_model(model, self.models)
