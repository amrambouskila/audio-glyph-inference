"""InferenceResult - one-shot generated contour and score response."""

from __future__ import annotations

from pydantic import BaseModel


class InferenceResult(BaseModel):
    """Response schema for POST /api/inference."""

    shape_distance: float
    contours: list[list[float]]
    target_contours: list[list[float]]
