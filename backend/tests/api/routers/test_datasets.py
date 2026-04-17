"""Tests for src/api/routers/datasets.py (Phase 1 scaffold)."""

from __future__ import annotations

from src.api.routers import datasets


def test_router_annotation_declared() -> None:
    assert "router" in datasets.__annotations__
