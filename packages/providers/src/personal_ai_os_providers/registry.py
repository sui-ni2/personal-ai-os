from __future__ import annotations

from .base import ProviderAdapter


class ProviderRegistry:
    def __init__(self, providers: list[ProviderAdapter]) -> None:
        self._providers = {provider.id: provider for provider in providers}

    def get(self, provider_id: str) -> ProviderAdapter:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise KeyError(f"Unknown provider: {provider_id}") from exc

    def describe(self) -> list[dict[str, object]]:
        return [provider.describe() for provider in self._providers.values()]
