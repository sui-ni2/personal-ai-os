from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from personal_ai_os_core import Message, MessageRole

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


class AnthropicAdapter:
    id = "anthropic"

    def __init__(
        self,
        api_key: str | None,
        models: tuple[str, ...],
        timeout_seconds: float = 90,
        max_retries: int = 2,
        retry_base_seconds: float = 0.25,
        *,
        endpoint: str = "https://api.anthropic.com/v1/messages",
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
        return {
            "x-api-key": str(self._api_key),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _payload_messages(
        self, messages: list[Message]
    ) -> tuple[str, list[dict[str, str]]]:
        system_text = "\n".join(
            message.content for message in messages if message.role == MessageRole.SYSTEM
        )
        chat_messages = [
            {"role": message.role.value, "content": message.content}
            for message in messages
            if message.role in {MessageRole.USER, MessageRole.ASSISTANT}
        ]
        return system_text, chat_messages

    def _payload(self, messages: list[Message], model: str, *, stream: bool) -> dict[str, Any]:
        system_text, chat_messages = self._payload_messages(messages)
        payload: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": 4096,
            "stream": stream,
        }
        if system_text:
            payload["system"] = system_text
        return payload

    async def request_tool(
        self, messages: list[Message], model: str, tool: ProviderTool
    ) -> ProviderToolCall:
        self._validate(model)
        safe_tool_name = provider_tool_name(tool.name)
        payload = self._payload(messages, model, stream=False)
        payload["tools"] = [
            {
                "name": safe_tool_name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
        ]
        payload["tool_choice"] = {
            "type": "tool",
            "name": safe_tool_name,
            "disable_parallel_tool_use": True,
        }
        item = await self._post_json(payload)
        try:
            call = next(value for value in item["content"] if value.get("type") == "tool_use")
            arguments = call["input"]
            if not isinstance(arguments, dict):
                raise TypeError
            if str(call["name"]) != safe_tool_name:
                raise TypeError
            return ProviderToolCall(
                id=str(call.get("id") or "anthropic-tool-call"),
                name=tool.name,
                arguments=arguments,
            )
        except (KeyError, StopIteration, TypeError) as exc:
            raise ProviderError(
                "Anthropic returned an invalid tool call", code="invalid_tool_call"
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
                    raise error_for_status("Anthropic", response.status_code)
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
                        "Anthropic request timed out", code="timeout", retryable=True
                    ) from exc
            except (httpx.HTTPError, ValueError) as exc:
                if attempt >= self._max_retries:
                    raise ProviderError(
                        "Anthropic request failed", code="network_error", retryable=True
                    ) from exc
            await retry_pause(attempt, self._retry_base_seconds)
        raise AssertionError("retry loop exhausted")

    async def stream(self, messages: list[Message], model: str) -> AsyncIterator[str]:
        self._validate(model)
        payload = self._payload(messages, model, stream=True)
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
        system_text, chat_messages = self._payload_messages(messages)
        chat_messages.extend(
            [
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": call.id,
                            "name": provider_tool_name(call.name),
                            "input": call.arguments,
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": call.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    ],
                },
            ]
        )
        payload: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": 4096,
            "stream": True,
        }
        if system_text:
            payload["system"] = system_text
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
                            raise error_for_status("Anthropic", response.status_code)
                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            item = json.loads(line[6:])
                            if item.get("type") == "message_stop":
                                completed = True
                                break
                            if item.get("type") != "content_block_delta":
                                continue
                            text = item.get("delta", {}).get("text")
                            if text:
                                emitted = True
                                yield str(text)
                if not completed:
                    raise ProviderStreamInterrupted(
                        "Anthropic stream ended before completion",
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
                        "Anthropic stream timed out", code="timeout", retryable=not emitted
                    ) from exc
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                if emitted or attempt >= self._max_retries:
                    raise ProviderStreamInterrupted(
                        "Anthropic stream was interrupted",
                        code="stream_interrupted",
                        retryable=not emitted,
                    ) from exc
            await retry_pause(attempt, self._retry_base_seconds)

    def _validate(self, model: str) -> None:
        if not self._api_key:
            raise ProviderNotConfigured("Anthropic is not configured on the server")
        validate_model(model, self.models)
