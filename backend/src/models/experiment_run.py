"""ExperimentRun — one configured search over a transform family.

An experiment pins: a transform family, a search strategy (coordinate
descent / CMA-ES / symbolic regression), a dataset split, a scoring
metric, and a compute budget. It produces candidate transforms.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ExperimentRun(BaseModel):
    """One configured search run."""

    id: UUID
    name: str
    family: str
    search_strategy: str = Field(
        description="One of: 'grid', 'cma-es', 'bayesian', 'symbolic-regression'.",
    )
    dataset_split: str = Field(
        description="Dataset slice used for fitting, e.g., 'train', 'train+val'.",
    )
    scoring_metric: str = Field(
        description="Shape-distance metric used for fitness; e.g., 'procrustes', 'frechet'.",
    )
    max_evaluations: int
    started_at: datetime
    completed_at: datetime | None = None
    best_candidate_id: UUID | None = None
