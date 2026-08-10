from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass, field

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from .config import Settings


COOKIE_NAME = "personal_ai_os_session"
PUBLIC_API_PATHS = {"/api/auth/status", "/api/auth/login", "/api/auth/logout"}


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _sign(settings: Settings, expires_at: int) -> str:
    assert settings.session_secret is not None
    payload = f"v1.{expires_at}"
    signature = hmac.new(
        settings.session_secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{payload}.{_encode(signature)}"


def _valid(settings: Settings, token: str | None) -> bool:
    if not settings.auth_required:
        return True
    if not token or not settings.session_secret:
        return False
    try:
        version, expires_raw, signature = token.split(".", 2)
        expires_at = int(expires_raw)
    except (ValueError, TypeError):
        return False
    if version != "v1" or expires_at <= int(time.time()):
        return False
    return hmac.compare_digest(token, _sign(settings, expires_at))


def _is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


@dataclass
class LoginLimiter:
    attempts: dict[str, list[float]] = field(default_factory=dict)
    window_seconds: int = 600
    max_attempts: int = 8

    def allow(self, key: str) -> bool:
        cutoff = time.monotonic() - self.window_seconds
        recent = [item for item in self.attempts.get(key, []) if item >= cutoff]
        self.attempts[key] = recent
        return len(recent) < self.max_attempts

    def record_failure(self, key: str) -> None:
        self.attempts.setdefault(key, []).append(time.monotonic())

    def clear(self, key: str) -> None:
        self.attempts.pop(key, None)


class AccessProtectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if (
            request.method == "OPTIONS"
            or not request.url.path.startswith("/api/")
            or request.url.path in PUBLIC_API_PATHS
            or _valid(self.settings, request.cookies.get(COOKIE_NAME))
        ):
            return await call_next(request)
        return JSONResponse(
            status_code=401,
            content={"detail": "Unlock Personal AI OS to continue", "code": "authentication_required"},
            headers={"Cache-Control": "no-store"},
        )


def create_auth_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["access"])
    limiter = LoginLimiter()

    @router.get("/status")
    def status(request: Request) -> dict[str, bool]:
        return {
            "required": settings.auth_required,
            "authenticated": _valid(settings, request.cookies.get(COOKIE_NAME)),
        }

    @router.post("/login")
    def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, bool]:
        if not settings.auth_required:
            return {"authenticated": True}
        client_key = request.client.host if request.client else "unknown"
        if not limiter.allow(client_key):
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")
        assert settings.access_password is not None
        if not hmac.compare_digest(payload.password, settings.access_password):
            limiter.record_failure(client_key)
            raise HTTPException(status_code=401, detail="The access password is incorrect")
        limiter.clear(client_key)
        expires_at = int(time.time()) + settings.access_session_hours * 3600
        response.set_cookie(
            COOKIE_NAME,
            _sign(settings, expires_at),
            max_age=settings.access_session_hours * 3600,
            httponly=True,
            secure=_is_https(request),
            samesite="lax",
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return {"authenticated": True}

    @router.post("/logout")
    def logout(request: Request, response: Response) -> dict[str, bool]:
        response.delete_cookie(
            COOKIE_NAME,
            httponly=True,
            secure=_is_https(request),
            samesite="lax",
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return {"authenticated": False}

    return router
