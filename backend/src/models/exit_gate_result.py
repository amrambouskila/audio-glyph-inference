"""ExitGateResult - verdict of the Phase-2 exit gate over a held-out evaluation.

Internal computational result (not an API or storage contract): produced by
baseline_thresholds.evaluate_exit_gate and reported in the Phase-5 writeup.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ExitGateResult(BaseModel):
    """Whether a search run cleared the leave-one-accent-out exit gate."""

    passed: bool = Field(description="True iff at least min_accents held-out accents each cleared their letter bar.")
    accents_passed: int = Field(
        ge=0,
        description="Number of held-out accents that met the per-accent letter requirement.",
    )
    letters_required: int = Field(
        ge=0,
        description="Per-accent letters that must be within threshold (ceil(fraction * L)).",
    )
    per_accent_pass_counts: dict[str, int] = Field(
        description="held-out accent -> count of letters within their exit threshold.",
    )

    @model_validator(mode="after")
    def _validate_counts(self) -> ExitGateResult:
        if any(count < 0 for count in self.per_accent_pass_counts.values()):
            raise ValueError("per_accent_pass_counts values must be non-negative")
        if self.accents_passed > len(self.per_accent_pass_counts):
            raise ValueError("accents_passed cannot exceed per_accent_pass_counts size")
        return self
