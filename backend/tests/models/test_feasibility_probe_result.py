"""Tests for src/models/feasibility_probe_result.py."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError
from src.models.feasibility_probe_result import FeasibilityProbeResult


def test_feasibility_probe_result_round_trips_metrics() -> None:
    result = FeasibilityProbeResult(
        verdict="FEASIBLE",
        d_probe_in=0.1,
        d_probe_out=0.2,
        d_const_in=0.3,
        d_const_out=0.4,
        d_global_in=0.5,
        delta_lookup=0.2,
        overfit_ratio=2.0,
        r_track=0.6,
    )
    assert result.model_dump()["verdict"] == "FEASIBLE"
    assert result.delta_lookup == 0.2


def test_feasibility_probe_result_rejects_nonfinite_or_negative_metrics() -> None:
    with pytest.raises(ValidationError, match="finite and non-negative"):
        FeasibilityProbeResult(
            verdict="NO_FIT",
            d_probe_in=math.nan,
            d_probe_out=0.2,
            d_const_in=0.3,
            d_const_out=0.4,
            d_global_in=0.5,
            delta_lookup=0.2,
            overfit_ratio=2.0,
            r_track=0.6,
        )
    with pytest.raises(ValidationError, match="finite and non-negative"):
        FeasibilityProbeResult(
            verdict="NO_FIT",
            d_probe_in=0.1,
            d_probe_out=-0.2,
            d_const_in=0.3,
            d_const_out=0.4,
            d_global_in=0.5,
            delta_lookup=0.2,
            overfit_ratio=2.0,
            r_track=0.6,
        )
    with pytest.raises(ValidationError, match="delta_lookup"):
        FeasibilityProbeResult(
            verdict="NO_FIT",
            d_probe_in=0.1,
            d_probe_out=0.2,
            d_const_in=0.3,
            d_const_out=0.4,
            d_global_in=0.5,
            delta_lookup=math.inf,
            overfit_ratio=2.0,
            r_track=0.6,
        )
