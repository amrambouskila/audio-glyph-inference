"""Tests for src/api/routers/experiments.py (Phase 2 scaffold)."""

from __future__ import annotations

from src.api.routers import experiments


def test_router_annotation_declared() -> None:
    assert "router" in experiments.__annotations__
