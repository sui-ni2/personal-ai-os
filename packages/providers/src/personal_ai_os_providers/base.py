from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from personal_ai_os_core import Message


class ProviderError(RuntimeError):
    pass


class ProviderNotConfigured(ProviderError):
    pass


class ProviderAdapter(Protocol):
    id: str
    models: tuple[str, ...]

    @property
    def configured(self) -> bool: ...

    async def stream(self, messages: list[Message], model: str) -> AsyncIterator[str]: ...

    def describe(self) -> dict[str, object]: ...


def validate_model(model: str, models: tuple[str, ...]) -> None:
    if model not in models:
        raise ProviderError(f"Model is not allowlisted for this provider: {model}")
