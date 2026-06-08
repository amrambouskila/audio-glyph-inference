"""Tests for src/api/routers/health.py."""

from __future__ import annotations


async def test_health_returns_ok(client) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
