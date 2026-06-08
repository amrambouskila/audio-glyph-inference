"""LeaveOneAccentOutResult - Phase-3 cross-accent evaluation report."""

from __future__ import annotations

from math import isfinite
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.constants import ACCENTS, HEBREW_LETTERS
from src.models.exit_gate_result import ExitGateResult


class LeaveOneAccentOutResult(BaseModel):
    """Fold-level distance table for leave-one-accent-out evaluation."""

    family: str = Field(min_length=1, description="Transform family evaluated across held-out accents.")
    search_strategy: str = Field(min_length=1, description="Search strategy used inside each fold.")
    scoring_metric: str = Field(min_length=1, description="Shape-distance metric used for fold fitting and scoring.")
    distances_by_accent: dict[str, dict[str, float]] = Field(
        description="held-out accent -> letter -> mean held-out shape distance.",
    )
    mean_distance_by_accent: dict[str, float] = Field(description="held-out accent -> mean held-out distance.")
    best_candidate_id_by_accent: dict[str, UUID] = Field(description="held-out accent -> best shared candidate id.")
    exit_gate: ExitGateResult | None = Field(description="Exit-gate verdict when thresholds are supplied.")

    @model_validator(mode="after")
    def _validate_result_maps(self) -> LeaveOneAccentOutResult:
        accent_keys = set(self.distances_by_accent)
        if accent_keys != set(self.mean_distance_by_accent) or accent_keys != set(self.best_candidate_id_by_accent):
            raise ValueError("leave-one-accent-out accent maps must have matching keys")
        unknown_accents = accent_keys.difference(ACCENTS)
        if unknown_accents:
            raise ValueError("leave-one-accent-out accents must be in constants.ACCENTS")
        for accent, distances in self.distances_by_accent.items():
            unknown_letters = set(distances).difference(HEBREW_LETTERS)
            if unknown_letters:
                raise ValueError(f"leave-one-accent-out letters for {accent} must be in constants.HEBREW_LETTERS")
            for distance in distances.values():
                if not isfinite(distance) or distance < 0.0:
                    raise ValueError("leave-one-accent-out distances must be finite and non-negative")
        if any(not isfinite(distance) or distance < 0.0 for distance in self.mean_distance_by_accent.values()):
            raise ValueError("leave-one-accent-out mean distances must be finite and non-negative")
        if self.exit_gate is not None and set(self.exit_gate.per_accent_pass_counts).difference(accent_keys):
            raise ValueError("exit-gate accent counts must be a subset of leave-one-accent-out accents")
        return self
