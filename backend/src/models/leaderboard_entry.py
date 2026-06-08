"""LeaderboardEntry - replayed per-family experiment ranking row."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    """One ranked candidate row in a per-family leaderboard."""

    family: str = Field(description="Transform family for the candidate.")
    run_id: UUID = Field(description="ExperimentRun id that produced the candidate.")
    run_name: str = Field(description="ExperimentRun name.")
    candidate_id: UUID = Field(description="TransformCandidate id.")
    search_strategy: str = Field(description="Search strategy used by the producing run.")
    scoring_metric: str = Field(description="Distance metric used by the producing run.")
    held_out_accent: str | None = Field(description="Held-out accent for the run, if any.")
    shared_across_letters: bool = Field(description="Whether the candidate is a shared-across-letters operator.")
    mean_shape_distance: float = Field(description="Lower-is-better mean shape distance.")
    simplicity_score: float = Field(description="Higher-is-better simplicity score.")
    interpretability_score: float = Field(description="Higher-is-better interpretability score.")
    lookup_ratio: float = Field(description="Anti-lookup diagnostic Var_within / Var_between.")
    created_at: datetime = Field(description="Candidate creation timestamp.")
