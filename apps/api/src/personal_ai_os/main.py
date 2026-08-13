from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from personal_ai_os_core import Capability

from .auth import AccessProtectionMiddleware, create_auth_router
from .config import Settings
from .p5_routes import router as p5_router
from .routes import router
from .runtime import Runtime, create_runtime


def create_app(settings: Settings | None = None, runtime: Runtime | None = None) -> FastAPI:
    app_runtime = runtime or create_runtime(settings or Settings.from_env())

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        app_runtime.database.migrate()
        app_runtime.database.sync_entitlements(
            {
                capability.value: app_runtime.product.allows(capability)
                for capability in Capability
            }
        )
        yield

    app = FastAPI(
        title="Personal AI OS API",
        version="0.1.0",
        description="Provider-neutral modular-monolith API with auditable execution traces.",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.runtime = app_runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_runtime.settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AccessProtectionMiddleware, settings=app_runtime.settings)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    app.include_router(router)
    app.include_router(p5_router)
    app.include_router(create_auth_router(app_runtime.settings))
    web_dir = os.getenv("PERSONAL_AI_OS_WEB_DIR")
    if web_dir:
        static_root = Path(web_dir).resolve()
        if not static_root.is_dir():
            raise RuntimeError(f"PERSONAL_AI_OS_WEB_DIR does not exist: {static_root}")
        app.mount("/", StaticFiles(directory=static_root, html=True), name="web")
    return app


app = create_app()
