"""Shared pytest fixtures for the audio-glyph-inference backend.

Integration tests hit a real Postgres, never a mock (CLAUDE.md §13). In CI the
Stage-2 `services: postgres` is used via BACKEND_DATABASE_URL; locally we spin a
disposable Postgres with testcontainers so `uv run pytest` needs nothing beyond Docker.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
import src.data.orm  # noqa: F401  (side-effect import: registers rows on Base.metadata)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from src.data.database import create_engine
from src.data.orm.base import Base


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    env_url = os.environ.get("BACKEND_DATABASE_URL")
    if env_url:
        yield env_url
        return
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest_asyncio.fixture
async def db_engine(postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(postgres_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


# --- API fixtures ---
FONT_PATH = Path(__file__).resolve().parent.parent / "data" / "fonts" / "StamAshkenazCLM.ttf"
FIXTURE_M4A = Path(__file__).resolve().parent / "fixtures" / "test-sample.m4a"


def build_settings(postgres_url: str, tmp_path: Path, **overrides: object):  # noqa: ANN201
    """Test BackendSettings: test DB + committed font + tmp data dirs, plus overrides."""
    from src.config import BackendSettings

    return BackendSettings(
        database_url=postgres_url,
        font_file=FONT_PATH,
        audio_dir=tmp_path / "audio",
        contours_dir=tmp_path / "contours",
        **overrides,
    )


@pytest_asyncio.fixture
async def client(db_engine: AsyncEngine, postgres_url: str, tmp_path: Path):  # noqa: ANN201
    from httpx import ASGITransport, AsyncClient
    from src.api.main import create_app

    app = create_app(settings=build_settings(postgres_url, tmp_path), engine=db_engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client
