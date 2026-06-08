"""InferenceRequest - one-shot candidate scoring request."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class InferenceRequest(BaseModel):
    """Request schema for POST /api/inference."""

    audio_sample_id: UUID
    candidate_id: UUID
    scoring_metric: Literal["procrustes", "frechet", "chamfer"] = "procrustes"
