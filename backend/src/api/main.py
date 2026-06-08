"""FastAPI application entrypoint for the audio-glyph-inference backend.

Phase 1 exposes: health + dataset ingestion/listing/glyph rendering.
Phase 2 adds: experiment run CRUD, candidate search jobs.
Phase 4 adds: WebSocket `/ws/live` for real-time pronunciation scoring.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from src.api.routers import datasets, experiments, health, inference, live
from src.config import BackendSettings, get_settings
from src.data.database import create_engine


def create_app(settings: BackendSettings | None = None, engine: AsyncEngine | None = None) -> FastAPI:
    """Build the FastAPI app. `engine` is injectable for tests; otherwise built from settings."""
    settings = settings or get_settings()
    engine = engine if engine is not None else create_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    app = FastAPI(title="audio-glyph-inference", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.include_router(health.router)
    app.include_router(datasets.router)
    app.include_router(experiments.router)
    app.include_router(inference.router)
    app.include_router(live.router)
    return app


app = create_app()
