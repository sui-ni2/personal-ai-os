from __future__ import annotations

from fastapi.testclient import TestClient

from personal_ai_os.config import Settings
from personal_ai_os.main import create_app


def protected_settings(runtime) -> Settings:
    source = runtime.settings
    return Settings(
        data_dir=source.data_dir,
        cors_origins=source.cors_origins,
        openai_models=source.openai_models,
        anthropic_models=source.anthropic_models,
        default_provider=source.default_provider,
        default_model=source.default_model,
        mcp_stdio_commands=source.mcp_stdio_commands,
        auth_required=True,
        access_password="correct horse battery staple",
        session_secret="test-session-secret-that-is-at-least-32-characters",
    )


def test_access_protection_is_optional(client: TestClient) -> None:
    assert client.get("/api/auth/status").json() == {
        "required": False,
        "authenticated": True,
    }
    assert client.get("/api/projects").status_code == 200


def test_protected_api_login_and_logout(runtime) -> None:
    runtime.settings = protected_settings(runtime)
    with TestClient(create_app(runtime=runtime)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/projects").status_code == 401
        assert client.get("/api/docs").status_code == 401
        assert client.get("/api/auth/status").json() == {
            "required": True,
            "authenticated": False,
        }

        rejected = client.post("/api/auth/login", json={"password": "wrong"})
        assert rejected.status_code == 401
        assert "personal_ai_os_session" not in client.cookies

        accepted = client.post(
            "/api/auth/login", json={"password": "correct horse battery staple"}
        )
        assert accepted.status_code == 200
        assert client.get("/api/projects").status_code == 200
        assert client.get("/api/docs").status_code == 200
        assert client.get("/api/auth/status").json()["authenticated"] is True

        assert client.post("/api/auth/logout").status_code == 200
        assert client.get("/api/projects").status_code == 401


def test_production_auth_configuration_fails_closed(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PERSONAL_AI_OS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PERSONAL_AI_OS_REQUIRE_AUTH", "true")
    monkeypatch.delenv("PERSONAL_AI_OS_ACCESS_PASSWORD", raising=False)
    monkeypatch.delenv("PERSONAL_AI_OS_SESSION_SECRET", raising=False)
    try:
        Settings.from_env()
    except RuntimeError as exc:
        assert "ACCESS_PASSWORD" in str(exc)
    else:
        raise AssertionError("public deployment must not start without an access password")


def test_production_auth_rejects_short_password(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PERSONAL_AI_OS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PERSONAL_AI_OS_REQUIRE_AUTH", "true")
    monkeypatch.setenv("PERSONAL_AI_OS_ACCESS_PASSWORD", "too-short")
    monkeypatch.setenv(
        "PERSONAL_AI_OS_SESSION_SECRET", "test-session-secret-that-is-at-least-32-characters"
    )
    try:
        Settings.from_env()
    except RuntimeError as exc:
        assert "at least 10" in str(exc)
    else:
        raise AssertionError("short public access passwords must be rejected")
