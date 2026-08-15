from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from personal_ai_os_core import Message

from .base import (
    ProviderError,
    ProviderNotConfigured,
    ProviderStreamInterrupted,
    ProviderTimeout,
    ProviderTool,
    ProviderToolCall,
    error_for_status,
    provider_tool_name,
    retry_pause,
    validate_model,
)


class OpenAIAdapter:
    id = "openai"
    provider_name = "OpenAI"

    def __init__(
        self,
        api_key: str | None,
        models: tuple[str, ...],
        timeout_seconds: float = 90,
        max_retries: int = 2,
        retry_base_seconds: float = 0.25,
        *,
        endpoint: str = "https://api.openai.com/v1/chat/completions",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self.models = models
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._retry_base_seconds = retry_base_seconds
        self._endpoint = endpoint
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def describe(self) -> dict[str, object]:
        return {"id": self.id, "configured": self.configured, "models": list(self.models)}

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def _messages(self, messages: list[Message]) -> list[dict[str, str]]:
        return [
            {"role": message.role.value, "content": message.content}
            for message in messages
        ]

    async def request_tool(
        self, messages: list[Message], model: str, tool: ProviderTool
    ) -> ProviderToolCall:
        self._validate(model)
        safe_tool_name = provider_tool_name(tool.name)
        payload = {
            "model": model,
            "messages": self._messages(messages),
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": safe_tool_name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                        "strict": True,
                    },
                }
            ],
            "tool_choice": "required",
            "stream": False,
        }
        item = await self._post_json(payload)
        try:
            call = item["choices"][0]["message"]["tool_calls"][0]
            arguments = json.loads(call["function"]["arguments"])
            if not isinstance(arguments, dict):
                raise TypeError
            if str(call["function"]["name"]) != safe_tool_name:
                raise TypeError
            return ProviderToolCall(
                id=str(call.get("id") or f"{self.id}-tool-call"),
                name=tool.name,
                arguments=arguments,
            )
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError(
                f"{self.provider_name} returned an invalid tool call",
                code="invalid_tool_call",
            ) from exc

    async def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self._timeout_seconds), transport=self._transport
                ) as client:
                    response = await client.post(
                        self._endpoint, headers=self._headers(), json=payload
                    )
                if response.is_error:
                    raise error_for_status(self.provider_name, response.status_code)
                item = response.json()
                if not isinstance(item, dict):
                    raise ValueError
                return item
            except ProviderError as exc:
                if not exc.retryable or attempt >= self._max_retries:
                    raise
            except httpx.TimeoutException as exc:
                if attempt >= self._max_retries:
                    raise ProviderTimeout(
                        f"{self.provider_name} request timed out",
                        code="timeout",
                        retryable=True,
                    ) from exc
            except (httpx.HTTPError, ValueError) as exc:
                if attempt >= self._max_retries:
                    raise ProviderError(
                        f"{self.provider_name} request failed",
                        code="network_error",
                        retryable=True,
                    ) from exc
            await retry_pause(attempt, self._retry_base_seconds)
        raise AssertionError("retry loop exhausted")

    async def stream(self, messages: list[Message], model: str) -> AsyncIterator[str]:
        self._validate(model)
        payload = {"model": model, "messages": self._messages(messages), "stream": True}
        async for chunk in self._stream_payload(payload):
            yield chunk

    async def stream_after_tool(
        self,
        messages: list[Message],
        model: str,
        call: ProviderToolCall,
        result: dict[str, Any],
    ) -> AsyncIterator[str]:
        self._validate(model)
        safe_name = provider_tool_name(call.name)
        followup_messages: list[dict[str, Any]] = list(self._messages(messages))
        followup_messages.extend(
            [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": safe_name,
                                "arguments": json.dumps(call.arguments, ensure_ascii=False),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                },
            ]
        )
        payload = {"model": model, "messages": followup_messages, "stream": True}
        async for chunk in self._stream_payload(payload):
            yield chunk

    async def _stream_payload(self, payload: dict[str, Any]) -> AsyncIterator[str]:
        for attempt in range(self._max_retries + 1):
            emitted = False
            completed = False
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self._timeout_seconds), transport=self._transport
                ) as client:
                    async with client.stream(
                        "POST", self._endpoint, headers=self._headers(), json=payload
                    ) as response:
                        if response.is_error:
                            raise error_for_status(self.provider_name, response.status_code)
                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data = line[6:]
                            if data == "[DONE]":
                                completed = True
                                break
                            item = json.loads(data)
                            delta = item.get("choices", [{}])[0].get("delta", {}).get("content")
                            if delta:
                                emitted = True
                                yield str(delta)
                if not completed:
                    raise ProviderStreamInterrupted(
                        f"{self.provider_name} stream ended before completion",
                        code="stream_interrupted",
                        retryable=not emitted,
                    )
                return
            except asyncio.CancelledError:
                raise
            except ProviderError as exc:
                if emitted or not exc.retryable or attempt >= self._max_retries:
                    raise
            except httpx.TimeoutException as exc:
                if emitted or attempt >= self._max_retries:
                    raise ProviderTimeout(
                        f"{self.provider_name} stream timed out",
                        code="timeout",
                        retryable=not emitted,
                    ) from exc
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                if emitted or attempt >= self._max_retries:
                    raise ProviderStreamInterrupted(
                        f"{self.provider_name} stream was interrupted",
                        code="stream_interrupted",
                        retryable=not emitted,
                    ) from exc
            await retry_pause(attempt, self._retry_base_seconds)

    def _validate(self, model: str) -> None:
        if not self._api_key:
            raise ProviderNotConfigured(
                f"{self.provider_name} is not configured on the server"
            )
        validate_model(model, self.models)
