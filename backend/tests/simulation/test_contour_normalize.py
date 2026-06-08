"""Tests for src/simulation/contour_normalize.py — closed-form unit-square normalization."""

from __future__ import annotations

import numpy as np
from src.simulation.contour_normalize import normalize_to_unit_square


def test_centered_contour_scaled_to_touch_box() -> None:
    contour = np.array([[2.0, 0.0], [0.0, 1.0], [-2.0, 0.0], [0.0, -1.0]])
    out = normalize_to_unit_square(contour)
    np.testing.assert_allclose(out, [[0.5, 0.0], [0.0, 0.25], [-0.5, 0.0], [0.0, -0.25]], atol=1e-12)


def test_offset_contour_is_recentered() -> None:
    contour = np.array([[1.0, 1.0], [3.0, 1.0], [3.0, 3.0], [1.0, 3.0]])
    out = normalize_to_unit_square(contour)
    np.testing.assert_allclose(out.mean(axis=0), [0.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(np.abs(out).max(), 0.5, atol=1e-12)


def test_degenerate_contour_does_not_blow_up() -> None:
    contour = np.full((4, 2), 5.0)
    out = normalize_to_unit_square(contour)
    assert out.dtype == np.float64
    assert np.all(np.isfinite(out))
    np.testing.assert_allclose(out, 0.0, atol=1e-9)
