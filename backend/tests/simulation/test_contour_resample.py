"""Tests for src/simulation/contour_resample.py — closed-form arc-length resampling."""

from __future__ import annotations

import numpy as np
from src.simulation.contour_resample import resample_closed


def test_unit_square_resampled_to_eight_points() -> None:
    square = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    out = resample_closed(square, 8)
    expected = np.array(
        [
            [0.0, 0.0],
            [0.5, 0.0],
            [1.0, 0.0],
            [1.0, 0.5],
            [1.0, 1.0],
            [0.5, 1.0],
            [0.0, 1.0],
            [0.0, 0.5],
        ]
    )
    np.testing.assert_allclose(out, expected, atol=1e-12)


def test_shape_and_dtype() -> None:
    square = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    out = resample_closed(square, 100)
    assert out.shape == (100, 2)
    assert out.dtype == np.float64


def test_circle_radius_preserved() -> None:
    theta = np.linspace(0.0, 2.0 * np.pi, 512, endpoint=False)
    circle = np.stack([np.cos(theta), np.sin(theta)], axis=1)
    out = resample_closed(circle, 64)
    np.testing.assert_allclose(np.hypot(out[:, 0], out[:, 1]), 1.0, atol=1e-4)
