"""FastAPI application entrypoint for the audio-glyph-inference backend.

Phase 1 exposes: health, dataset ingestion/listing, glyph rendering.
Phase 2 adds: experiment run CRUD, candidate search jobs.
Phase 3 adds: symbolic-regression proposal endpoints.
Phase 4 adds: WebSocket `/ws/live` for real-time pronunciation scoring.
"""
from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Build the FastAPI app instance. See routers/ for concrete endpoints."""
    raise NotImplementedError


app: FastAPI  # populated at import time once create_app is implemented