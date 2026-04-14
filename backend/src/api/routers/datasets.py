"""Paired-example dataset ingestion and listing (Phase 1).

Endpoints:
  POST /api/datasets/audio       — upload a user-recorded .m4a file
                                   (accepts audio/mp4, audio/x-m4a, audio/aac)
                                   + form fields: letter, accent, repetition.
                                   Decoded via librosa+audioread (ffmpeg
                                   backend) at ingestion time.
  POST /api/datasets/glyphs      — render + store a target glyph contour
  POST /api/datasets/pairs       — associate audio ↔ glyph into a paired example
  GET  /api/datasets/pairs       — list paired examples
"""
from __future__ import annotations

from fastapi import APIRouter

router: APIRouter  # built in Phase 1 implementation