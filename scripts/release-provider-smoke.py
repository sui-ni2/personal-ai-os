from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
KEY_ENV = {
    "openai": "PERSONAL_AI_OS_OPENAI_API_KEY",
    "anthropic": "PERSONAL_AI_OS_ANTHROPIC_API_KEY",
}
ALL_SECRET_ENV = tuple(KEY_ENV.values()) + ("PERSONAL_AI_OS_REALTIME_API_KEY",)


class SmokeFailure(RuntimeError):
    pass


def _pass(message: str) -> None:
    print(f"[PASS] {message}")


def _fail(message: str) -> None:
    raise SmokeFailure(message)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _environment(data_dir: Path, *, provider: str, include_credential: bool) -> dict[str, str]:
    env = os.environ.copy()
    credential = env.get(KEY_ENV[provider], "")
    for name in ALL_SECRET_ENV:
        env.pop(name, None)
    env["PERSONAL_AI_OS_DATA_DIR"] = str(data_dir)
    env["PERSONAL_AI_OS_REQUIRE_AUTH"] = "false"
    env["PYTHONUNBUFFERED"] = "1"
    if include_credential:
        if not credential:
            _fail(f"Missing required server-side credential environment variable: {KEY_ENV[provider]}")
        env[KEY_ENV[provider]] = credential
    return env


def _start_api(env: dict[str, str]) -> tuple[subprocess.Popen[bytes], str]:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "personal_ai_os.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
            "--no-access-log",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if process.poll() is not None:
            _fail("API exited before becoming healthy")
        try:
            response = httpx.get(f"{base_url}/health", timeout=1.5)
            if response.status_code == 200 and response.json().get("status") == "ok":
                return process, base_url
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(0.25)
    process.terminate()
    _fail("API did not become healthy within 25 seconds")


def _stop_api(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def _json(client: httpx.Client, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        _fail(f"{method} {path} returned HTTP {response.status_code}")
    try:
        payload = response.json()
    except ValueError:
        _fail(f"{method} {path} did not return JSON")
    if not isinstance(payload, dict):
        _fail(f"{method} {path} returned an unexpected payload")
    return payload


def _provider(client: httpx.Client, provider_id: str) -> dict[str, Any]:
    items = _json(client, "GET", "/api/providers").get("items")
    if not isinstance(items, list):
        _fail("Provider list is missing")
    for item in items:
        if isinstance(item, dict) and item.get("id") == provider_id:
            return item
    _fail(f"Provider is not registered: {provider_id}")


def _chat(client: httpx.Client, provider: str, model: str, content: str, conversation_id: str | None = None) -> str:
    payload: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "project_id": "general",
        "content": content,
    }
    if conversation_id:
        payload["conversation_id"] = conversation_id
    response = client.post("/api/chat/stream", json=payload, timeout=150)
    if response.status_code != 200:
        _fail(f"POST /api/chat/stream returned HTTP {response.status_code}")

    events: list[dict[str, Any]] = []
    for line in response.text.splitlines():
        if not line.startswith("data: "):
            continue
        try:
            item = json.loads(line[6:])
        except json.JSONDecodeError:
            _fail("Chat stream emitted invalid SSE JSON")
        if isinstance(item, dict):
            events.append(item)
    if not events:
        _fail("Chat stream emitted no execution events")
    errors = [item for item in events if item.get("type") == "error"]
    if errors:
        code = ((errors[-1].get("payload") or {}).get("code") if isinstance(errors[-1].get("payload"), dict) else None)
        _fail(f"Chat stream reported a provider/application error{f' ({code})' if code else ''}")
    done = next((item for item in reversed(events) if item.get("type") == "done"), None)
    if not done or done.get("status") != "succeeded":
        _fail("Chat stream did not finish successfully")
    done_payload = done.get("payload")
    if not isinstance(done_payload, dict) or not done_payload.get("conversation_id"):
        _fail("Successful chat did not return a conversation id")
    return str(done_payload["conversation_id"])


def _assert_conversation(client: httpx.Client, conversation_id: str, minimum_messages: int) -> None:
    detail = _json(client, "GET", f"/api/conversations/{conversation_id}")
    messages = detail.get("messages")
    if not isinstance(messages, list) or len(messages) < minimum_messages:
        _fail("Conversation history did not persist the expected messages")
    if any(not isinstance(item, dict) for item in messages):
        _fail("Conversation history returned malformed messages")
    assistant = [item for item in messages if item.get("role") == "assistant"]
    if not assistant or not all(str(item.get("content") or "").strip() for item in assistant):
        _fail("Provider returned an empty assistant message")


def run(provider: str, requested_model: str | None) -> None:
    if provider not in KEY_ENV:
        _fail(f"Unsupported provider: {provider}")
    if not os.getenv(KEY_ENV[provider]):
        _fail(f"Set {KEY_ENV[provider]} in the current shell; the script never prints or writes its value")

    with tempfile.TemporaryDirectory(prefix="personal-ai-os-release-smoke-") as temp_dir:
        data_dir = Path(temp_dir)

        # Phase 1: fresh install with no provider credential.
        process, base_url = _start_api(_environment(data_dir, provider=provider, include_credential=False))
        try:
            with httpx.Client(base_url=base_url, timeout=20) as client:
                health = _json(client, "GET", "/health")
                if health.get("version") != "0.2.0":
                    _fail("Runtime health version is not aligned to v0.2.0")
                item = _provider(client, provider)
                if item.get("configured") is not False:
                    _fail("Fresh no-key startup unexpectedly reports the provider as configured")
                settings = _json(client, "GET", "/api/settings")
                secrets = settings.get("secrets")
                if secrets != {"storage": "environment", "values_exposed": False}:
                    _fail("Settings secret boundary is not fail-closed")
            _pass("fresh install starts safely with provider unconfigured and secrets hidden")
        finally:
            _stop_api(process)

        # Phase 2: restart with the real credential and exercise a complete chat turn.
        process, base_url = _start_api(_environment(data_dir, provider=provider, include_credential=True))
        try:
            with httpx.Client(base_url=base_url, timeout=30) as client:
                item = _provider(client, provider)
                models = item.get("models")
                if not isinstance(models, list) or not models:
                    _fail("Configured provider has no allowlisted models")
                model = requested_model or str(models[0])
                if model not in models:
                    _fail(f"Requested model is not allowlisted for {provider}: {model}")
                checked = _json(client, "POST", f"/api/providers/{provider}/check")
                if checked.get("status") != "connected":
                    _fail(f"Live provider connection check did not connect (status={checked.get('status')})")
                saved = _json(
                    client,
                    "PATCH",
                    "/api/settings",
                    json={"default_provider": provider, "default_model": model},
                )
                if saved.get("default_provider") != provider or saved.get("default_model") != model:
                    _fail("Provider/model selection was not persisted")
                conversation_id = _chat(client, provider, model, "Reply with exactly SMOKE_OK.")
                _assert_conversation(client, conversation_id, 2)
            _pass("real provider connects, saves model selection, and completes a text-chat turn")
        finally:
            _stop_api(process)

        # Phase 3: restart again against the same isolated data directory and verify persistence.
        process, base_url = _start_api(_environment(data_dir, provider=provider, include_credential=True))
        try:
            with httpx.Client(base_url=base_url, timeout=30) as client:
                settings = _json(client, "GET", "/api/settings")
                if settings.get("default_provider") != provider or settings.get("default_model") != model:
                    _fail("Provider/model selection did not survive API restart")
                _assert_conversation(client, conversation_id, 2)
                continued_id = _chat(
                    client,
                    provider,
                    model,
                    "Reply with exactly RESTART_OK.",
                    conversation_id=conversation_id,
                )
                if continued_id != conversation_id:
                    _fail("Conversation id changed after restart")
                _assert_conversation(client, conversation_id, 4)
            _pass("provider/model and conversation state survive restart; continued chat succeeds")
        finally:
            _stop_api(process)

    _pass("release provider smoke gate completed with isolated temporary runtime data")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed v0.2.0 real-provider smoke test. Never prints provider credentials or response text."
    )
    parser.add_argument("--provider", choices=sorted(KEY_ENV), default="openai")
    parser.add_argument("--model", default=None, help="Optional allowlisted model override")
    args = parser.parse_args()
    try:
        run(args.provider, args.model)
    except SmokeFailure as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
