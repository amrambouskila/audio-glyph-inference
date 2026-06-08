"""ExperimentCreate - request body for starting a Phase-2 search."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.constants import ACCENTS
from src.models.experiment_run import ScoringMetric, SearchStrategy


class ExperimentCreate(BaseModel):
    """Request schema for POST /api/experiments."""

    name: str
    family: str
    search_strategy: SearchStrategy
    dataset_split: str = "train"
    scoring_metric: ScoringMetric = "procrustes"
    regularization_weight: float = Field(ge=0.0)
    max_evaluations: int = Field(gt=0)
    held_out_accent: str | None = None
    rng_seed: int
    shared_across_letters: bool = True

    @field_validator("held_out_accent")
    @classmethod
    def _accent_in_vocabulary(cls, value: str | None) -> str | None:
        if value is not None and value not in ACCENTS:
            raise ValueError(f"held_out_accent must be one of constants.ACCENTS or None, got {value!r}")
        return value
