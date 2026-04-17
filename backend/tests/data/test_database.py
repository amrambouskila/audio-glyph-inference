"""Tests for src/data/database.py.

Phase 1 is scaffold-only: both callables raise NotImplementedError.
Real engine / session lifecycle tests land when Phase 1 implements the
bodies (see docs/phases/phase-1-plan.md). Per CLAUDE.md §13 the gate is
only real integration tests once the bodies exist — mocking the engine
is forbidden.
"""

from __future__ import annotations

import pytest
from src.data.database import create_engine, session_scope


def test_create_engine_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        create_engine("postgresql+asyncpg://user:pw@host:5432/db")


async def test_session_scope_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        await session_scope(engine=None)  # type: ignore[arg-type]
