from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from typing import Protocol

from personal_ai_os_core import Message


class ProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "provider_error",
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable


class ProviderNotConfigured(ProviderError):
    pass


class ProviderRateLimited(ProviderError):
    pass


class ProviderTimeout(ProviderError):
    pass


class ProviderCancelled(ProviderError):
    pass


class ProviderStreamInterrupted(ProviderError):
    pass


@dataclass(frozen=True)
class ProviderTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    suggested_arguments: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProviderToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


class ProviderAdapter(Protocol):
    id: str
    models: tuple[str, ...]

    @property
    def configured(self) -> bool: ...

    async def stream(self, messages: list[Message], model: str) -> AsyncIterator[str]: ...

    async def request_tool(
        self, messages: list[Message], model: str, tool: ProviderTool
    ) -> ProviderToolCall: ...

    async def stream_after_tool(
        self,
        messages: list[Message],
        model: str,
        call: ProviderToolCall,
        result: dict[str, Any],
    ) -> AsyncIterator[str]: ...

    def describe(self) -> dict[str, object]: ...


def validate_model(model: str, models: tuple[str, ...]) -> None:
    if model not in models:
        raise ProviderError(f"Model is not allowlisted for this provider: {model}")


def error_for_status(provider: str, status_code: int) -> ProviderError:
    if status_code == 429:
        return ProviderRateLimited(
            f"{provider} rate limit reached",
            code="rate_limited",
            status_code=status_code,
            retryable=True,
        )
    retryable = status_code in {408, 409} or status_code >= 500
    return ProviderError(
        f"{provider} request failed with HTTP {status_code}",
        code="upstream_http_error",
        status_code=status_code,
        retryable=retryable,
    )


async def retry_pause(attempt: int, base_seconds: float) -> None:
    await asyncio.sleep(min(base_seconds * (2**attempt), 2.0))


def provider_tool_name(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:64]
    if not normalized:
        raise ProviderError("Tool name cannot be represented by provider", code="invalid_tool_name")
    return normalized
