from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from personal_ai_os_core import Message

from .base import ProviderError, ProviderNotConfigured, validate_model


class OpenAIAdapter:
    id = "openai"

    def __init__(self, api_key: str | None, models: tuple[str, ...], timeout_seconds: float = 90) -> None:
        self._api_key = api_key
        self.models = models
        self._timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def describe(self) -> dict[str, object]:
        return {"id": self.id, "configured": self.configured, "models": list(self.models)}

    async def stream(self, messages: list[Message], model: str) -> AsyncIterator[str]:
        if not self._api_key:
            raise ProviderNotConfigured("OpenAI is not configured on the server")
        validate_model(model, self.models)
        payload = {
            "model": model,
            "messages": [{"role": message.role.value, "content": message.content} for message in messages],
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        item = json.loads(data)
                        delta = item.get("choices", [{}])[0].get("delta", {}).get("content")
                        if delta:
                            yield delta
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"OpenAI request failed with HTTP {exc.response.status_code}") from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise ProviderError("OpenAI streaming request failed") from exc
