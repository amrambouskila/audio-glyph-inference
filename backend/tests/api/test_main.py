"""Tests for src/api/main.py."""

from __future__ import annotations

from fastapi import FastAPI
from src.api.main import app, create_app


def test_module_app_is_fastapi() -> None:
    assert isinstance(app, FastAPI)


def test_create_app_builds_fastapi_without_overrides() -> None:
    assert isinstance(create_app(), FastAPI)


async def test_lifespan_disposes_engine() -> None:
    built = create_app()
    async with built.router.lifespan_context(built):
        pass
