"""Tests for src/api/routers/inference.py (Phase 2 scaffold)."""

from __future__ import annotations

from src.api.routers import inference


def test_router_annotation_declared() -> None:
    assert "router" in inference.__annotations__
