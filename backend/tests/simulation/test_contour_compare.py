"""Tests for src/simulation/contour_compare.py."""

from __future__ import annotations

import numpy as np
import pytest
from src.simulation.contour_compare import contour_compare
from src.simulation.shape_distance import chamfer_distance, frechet_distance, procrustes_distance


def _contour() -> np.ndarray:
    return np.array([[0.5, 0.0], [0.0, 0.5], [-0.5, 0.0], [0.0, -0.5]], dtype=np.float64)


@pytest.mark.parametrize(
    ("metric", "fn"),
    [("procrustes", procrustes_distance), ("chamfer", chamfer_distance), ("frechet", frechet_distance)],
)
def test_dispatches_to_each_metric(metric, fn) -> None:
    a = _contour()
    b = np.roll(a, 1, axis=0) * 0.8
    assert contour_compare(a, b, metric) == fn(a, b)


def test_unknown_metric_raises() -> None:
    a = _contour()
    with pytest.raises(ValueError, match="unknown metric"):
        contour_compare(a, a, "euclidean")
