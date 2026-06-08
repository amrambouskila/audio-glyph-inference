"""Alembic 0002 reflection tests for experiment tables."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine
from src.data.orm.experiment_run_row import ExperimentRunRow
from src.data.orm.transform_candidate_row import TransformCandidateRow


async def _drop_public_schema(database_url: str) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.exec_driver_sql("DROP SCHEMA public CASCADE")
        await connection.exec_driver_sql("CREATE SCHEMA public")
    await engine.dispose()


async def _reflected_columns(database_url: str) -> dict[str, set[str]]:
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        reflected = await connection.run_sync(
            lambda sync_connection: {
                table_name: {column["name"] for column in inspect(sync_connection).get_columns(table_name)}
                for table_name in ("experiment_runs", "transform_candidates")
            }
        )
    await engine.dispose()
    return reflected


def _upgrade(database_url: str) -> None:
    config = Config(str(Path("alembic.ini")))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


async def test_0002_migration_columns_match_orm(postgres_url: str, monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_DATABASE_URL", postgres_url)
    await _drop_public_schema(postgres_url)

    await asyncio.to_thread(_upgrade, postgres_url)
    reflected = await _reflected_columns(postgres_url)

    assert reflected["experiment_runs"] == set(ExperimentRunRow.__table__.columns.keys())
    assert reflected["transform_candidates"] == set(TransformCandidateRow.__table__.columns.keys())
    await _drop_public_schema(postgres_url)
