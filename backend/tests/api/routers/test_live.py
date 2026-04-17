"""Tests for src/api/routers/live.py (Phase 4 scaffold)."""

from __future__ import annotations

from src.api.routers import live


def test_router_annotation_declared() -> None:
    assert "router" in live.__annotations__
