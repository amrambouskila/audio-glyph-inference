"""ExperimentDetail - run detail response with best candidate metadata."""

from __future__ import annotations

from pydantic import BaseModel

from src.models.experiment_run import ExperimentRun
from src.models.transform_candidate import TransformCandidate


class ExperimentDetail(BaseModel):
    """Response schema for GET /api/experiments/{id}."""

    run: ExperimentRun
    best_candidate: TransformCandidate | None
    candidate_count: int
