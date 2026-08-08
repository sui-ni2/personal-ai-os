from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from personal_ai_os_core import Message, MessageRole

from .base import ProviderError, ProviderNotConfigured, validate_model


class AnthropicAdapter:
    id = "anthropic"

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
            raise ProviderNotConfigured("Anthropic is not configured on the server")
        validate_model(model, self.models)
        system_text = "\n".join(message.content for message in messages if message.role == MessageRole.SYSTEM)
        chat_messages = [
            {"role": message.role.value, "content": message.content}
            for message in messages
            if message.role in {MessageRole.USER, MessageRole.ASSISTANT}
        ]
        payload: dict[str, object] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": 4096,
            "stream": True,
        }
        if system_text:
            payload["system"] = system_text
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        item = json.loads(line[6:])
                        if item.get("type") != "content_block_delta":
                            continue
                        text = item.get("delta", {}).get("text")
                        if text:
                            yield text
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"Anthropic request failed with HTTP {exc.response.status_code}") from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise ProviderError("Anthropic streaming request failed") from exc
