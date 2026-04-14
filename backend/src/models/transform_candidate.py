"""TransformCandidate — a parameterized operator F_θ: audio -> geometry.

A candidate is a specific transform family plus a frozen parameter
vector θ. Candidates are the searchable objects; experiments produce
and rank them.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TransformCandidate(BaseModel):
    """A frozen candidate transform F_θ produced by a search run."""

    id: UUID
    family: str = Field(
        description=(
            "Name of the transform family registered in simulation/transforms/. "
            "E.g., 'fourier_series', 'lissajous', 'phase_space_embedding'."
        ),
    )
    theta: dict[str, float] = Field(
        description="Fitted parameter vector θ*; keys are family-specific parameter names.",
    )
    shared_across_letters: bool = Field(
        description="Whether θ is shared for every letter (True) or letter-specific (False).",
    )
    interpretability_score: float = Field(
        description="[0,1] — higher is more interpretable; penalizes parameter count and opacity.",
    )
    simplicity_score: float = Field(
        description="[0,1] — higher is simpler; typically 1/(1+MDL).",
    )
    mean_shape_distance: float = Field(
        description="Average Procrustes / Fréchet distance over evaluation split, units: normalized.",
    )
    created_at: datetime