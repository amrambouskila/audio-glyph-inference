"""TransformCandidate — a parameterized operator F_θ: audio -> geometry.

A candidate is a specific transform family plus a frozen parameter
vector θ. Candidates are the searchable objects; experiments produce
and rank them.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Widened θ value type (master plan §3.5): families need ints (Fourier order
# K), variable-length coefficient lists, and categorical/symbolic tags — not
# just floats. Mirrored by transform_base.Theta and persisted as JSONB.
ThetaValue = float | int | list[float] | str


class TransformCandidate(BaseModel):
    """A frozen candidate transform F_θ produced by a search run."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family: str = Field(
        description=(
            "Name of the transform family registered in simulation/transforms/. "
            "E.g., 'fourier_series', 'lissajous', 'phase_space_embedding'."
        ),
    )
    theta: dict[str, ThetaValue] = Field(
        description="Fitted parameter vector θ*; keys are family-specific parameter names.",
    )
    expression: str | None = Field(
        default=None,
        description="Closed-form expression for symbolic-regression candidates; None for parametric families.",
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
        description="Mean of the run's scoring_metric over the evaluation split, units: normalized.",
    )
    lookup_ratio: float = Field(
        description="Var_within / Var_between anti-lookup diagnostic on aligned generated contours.",
    )
    created_at: datetime
