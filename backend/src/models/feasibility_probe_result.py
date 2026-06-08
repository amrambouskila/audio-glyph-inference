"""FeasibilityProbeResult - synthetic/real-data entry-gate verdict."""

from __future__ import annotations

from math import isfinite
from typing import Literal

from pydantic import BaseModel, Field, field_validator

FeasibilityVerdict = Literal["FEASIBLE", "TRIVIAL_LOOKUP", "NO_FIT"]


class FeasibilityProbeResult(BaseModel):
    """Metrics and verdict from the Phase-2 feasibility probe."""

    verdict: FeasibilityVerdict = Field(description="Entry-gate verdict for the tested held-out accent.")
    d_probe_in: float = Field(description="Mean probe distance on fitted accents.")
    d_probe_out: float = Field(description="Mean probe distance on the held-out accent.")
    d_const_in: float = Field(description="Mean per-letter-constant distance on fitted accents.")
    d_const_out: float = Field(description="Mean per-letter-constant distance on the held-out accent.")
    d_global_in: float = Field(description="Mean global-constant distance on fitted accents.")
    delta_lookup: float = Field(description="d_const_out - d_probe_out.")
    overfit_ratio: float = Field(description="d_probe_out / d_probe_in, with finite zero-floor guarding.")
    r_track: float = Field(description="Held-out lookup ratio Var_within / Var_between.")

    @field_validator(
        "d_probe_in",
        "d_probe_out",
        "d_const_in",
        "d_const_out",
        "d_global_in",
        "overfit_ratio",
        "r_track",
    )
    @classmethod
    def _validate_non_negative_finite(cls, value: float) -> float:
        if not isfinite(value) or value < 0.0:
            raise ValueError("metric must be finite and non-negative")
        return value

    @field_validator("delta_lookup")
    @classmethod
    def _validate_finite_delta(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("delta_lookup must be finite")
        return value
