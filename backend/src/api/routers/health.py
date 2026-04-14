"""Liveness/readiness endpoints. Used by the Docker healthcheck."""
from __future__ import annotations

from fastapi import APIRouter

router: APIRouter  # built in Phase 1 implementation