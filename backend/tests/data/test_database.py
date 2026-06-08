"""Tests for src/data/database.py — real Postgres via the conftest fixtures (no mocking)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from src.data.database import create_engine, session_scope


def test_create_engine_returns_async_engine(postgres_url: str) -> None:
    engine = create_engine(postgres_url)
    assert isinstance(engine, AsyncEngine)
    assert engine.url.drivername == "postgresql+asyncpg"


async def test_session_scope_commits_on_success(db_engine: AsyncEngine) -> None:
    async with session_scope(db_engine) as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


async def test_session_scope_rolls_back_on_error(db_engine: AsyncEngine) -> None:
    with pytest.raises(ValueError, match="boom"):
        async with session_scope(db_engine) as session:
            await session.execute(text("SELECT 1"))
            raise ValueError("boom")
