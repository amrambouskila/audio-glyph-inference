"""Tests for src/simulation/scoring.py — closed-form score checks."""

from __future__ import annotations

import numpy as np
from src.simulation.scoring import interpretability_score, simplicity_score


def test_simplicity_is_one_at_zero_complexity() -> None:
    assert simplicity_score(0.0, 50.0) == 1.0


def test_simplicity_is_half_at_c_scale() -> None:
    assert simplicity_score(50.0, 50.0) == 0.5


def test_simplicity_decreases_with_complexity() -> None:
    assert simplicity_score(100.0, 50.0) < simplicity_score(10.0, 50.0)


def test_simplicity_closed_form() -> None:
    np.testing.assert_allclose(simplicity_score(30.0, 50.0), 1.0 / 1.6, atol=1e-12)


def test_interpretability_is_simplicity_times_prior() -> None:
    np.testing.assert_allclose(interpretability_score(50.0, 0.8, 50.0), 0.5 * 0.8, atol=1e-12)


def test_interpretability_equals_simplicity_at_unit_prior() -> None:
    assert interpretability_score(30.0, 1.0, 50.0) == simplicity_score(30.0, 50.0)
