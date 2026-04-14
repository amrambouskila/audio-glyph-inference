"""One-shot inference endpoint (Phase 2+).

Given an audio sample and a frozen candidate transform F_θ, compute the
generated geometry and its shape distance to the target glyph.
"""
from __future__ import annotations

from fastapi import APIRouter

router: APIRouter  # built in Phase 2 implementation