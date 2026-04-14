"""SQLAlchemy 2.0 async engine + session factory."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


def create_engine(database_url: str) -> AsyncEngine:
    """Build the async SQLAlchemy engine for a given DATABASE_URL."""
    raise NotImplementedError


async def session_scope(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession bound to the engine, committing on success."""
    raise NotImplementedError