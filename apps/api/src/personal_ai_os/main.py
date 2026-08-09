from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .p5_routes import router as p5_router
from .routes import router
from .runtime import Runtime, create_runtime


def create_app(settings: Settings | None = None, runtime: Runtime | None = None) -> FastAPI:
    app_runtime = runtime or create_runtime(settings or Settings.from_env())

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        app_runtime.database.migrate()
        yield

    app = FastAPI(
        title="Personal AI OS API",
        version="0.1.0",
        description="Provider-neutral modular-monolith API with auditable execution traces.",
        lifespan=lifespan,
    )
    app.state.runtime = app_runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_runtime.settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    app.include_router(router)
    app.include_router(p5_router)
    return app


app = create_app()
