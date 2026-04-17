"""Tests for src/api/routers/health.py (Phase 1 scaffold)."""

from __future__ import annotations

from src.api.routers import health


def test_router_annotation_declared() -> None:
    assert "router" in health.__annotations__
