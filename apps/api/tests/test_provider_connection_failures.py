from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from personal_ai_os_providers import ProviderRateLimited


def test_provider_connection_check_explains_rate_limit(
    client: TestClient,
    runtime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def limited_stream(messages, model):
        if False:
            yield ""
        raise ProviderRateLimited(
            "rate limited",
            code="rate_limited",
            status_code=429,
            retryable=True,
        )

    monkeypatch.setattr(runtime.providers.get("openai"), "stream", limited_stream)

    checked = client.post("/api/providers/openai/check")

    assert checked.status_code == 200
    assert checked.json() == {
        "provider": "openai",
        "status": "limited",
        "message": "The provider responded, but its rate or quota limit was reached.",
    }
