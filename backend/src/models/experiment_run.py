"""ExperimentRun — one configured search over a transform family.

An experiment pins: a transform family, a search strategy (grid / CMA-ES /
bayesian / symbolic regression), a dataset split, a scoring metric, the
§2-objective regularization weight, and everything needed to reproduce the
run (RNG seed, font, config snapshot). It produces candidate transforms.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.constants import ACCENTS

SearchStrategy = Literal["grid", "cma-es", "bayesian", "symbolic-regression"]
ScoringMetric = Literal["procrustes", "frechet", "chamfer"]


class ExperimentRun(BaseModel):
    """One configured search run.

    Records everything needed to reproduce the run (master plan §10): the RNG
    seed, the glyph font, a config snapshot, the search strategy, and which
    accent (if any) was held out for leave-one-accent-out evaluation (§11.3).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    family: str
    search_strategy: SearchStrategy
    dataset_split: str = Field(
        description="Dataset slice used for fitting, e.g., 'train', 'train+val'.",
    )
    scoring_metric: ScoringMetric
    regularization_weight: float = Field(
        ge=0.0,
        description="λ in the §2 objective: weight on Complexity(F_θ) relative to shape distance.",
    )
    held_out_accent: str | None = Field(
        default=None,
        description="Accent held out for leave-one-accent-out eval; None if no accent is held out (§11.3).",
    )
    rng_seed: int = Field(
        description="Search RNG seed; recorded for reproducibility (master plan §10).",
    )
    font_name: str = Field(
        description="Glyph font used for the target contours; recorded for reproducibility.",
    )
    config_snapshot: dict[str, str | int | float | bool] = Field(
        description="Flattened BackendSettings used for the run; recorded for reproducibility.",
    )
    max_evaluations: int
    started_at: datetime
    completed_at: datetime | None = None
    best_candidate_id: UUID | None = None

    @field_validator("held_out_accent")
    @classmethod
    def _accent_in_vocabulary(cls, value: str | None) -> str | None:
        if value is not None and value not in ACCENTS:
            raise ValueError(f"held_out_accent must be one of constants.ACCENTS or None, got {value!r}")
        return value
