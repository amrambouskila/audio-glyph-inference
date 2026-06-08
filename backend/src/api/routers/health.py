"""Liveness/readiness endpoint. Used by the Docker healthcheck."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return 200 with a static OK body."""
    return {"status": "ok"}
