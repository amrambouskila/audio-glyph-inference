"""Tests for src/simulation/contour_io.py."""

from __future__ import annotations

import numpy as np
from src.simulation.contour_io import load_contours, save_contours


def test_round_trip_preserves_order_and_values(tmp_path) -> None:
    contours = [
        np.array([[0.0, 0.1], [0.2, 0.3]], dtype=np.float64),
        np.array([[1.0, 1.1], [1.2, 1.3], [1.4, 1.5]], dtype=np.float64),
    ]
    path = tmp_path / "contours.npz"
    save_contours(path, contours)

    loaded = load_contours(path)
    assert len(loaded) == 2
    np.testing.assert_allclose(loaded[0], contours[0])
    np.testing.assert_allclose(loaded[1], contours[1])
