"""Tests for src/simulation/batch_procrustes.py."""

from __future__ import annotations

import numpy as np
from src.simulation.batch_procrustes import chamfer_distance_batch, procrustes_distance_batch
from src.simulation.shape_distance import chamfer_distance, procrustes_distance


def _contours() -> tuple[np.ndarray, np.ndarray]:
    t = 2.0 * np.pi * np.arange(32) / 32
    circle = np.stack([0.5 * np.cos(t), 0.5 * np.sin(t)], axis=1)
    ellipse = np.stack([0.5 * np.cos(t), 0.25 * np.sin(t)], axis=1)
    shifted = ellipse + np.array([0.1, -0.2])
    generated = np.stack([circle, ellipse, np.zeros_like(circle)])
    targets = np.stack([np.roll(circle, 3, axis=0), shifted, circle])
    return generated.astype(np.float64), targets.astype(np.float64)


def test_procrustes_distance_batch_matches_scalar_metric() -> None:
    generated, targets = _contours()
    distances = procrustes_distance_batch(generated, targets)
    expected = np.array([procrustes_distance(generated[i], targets[i]) for i in range(len(generated))])
    assert distances.dtype == np.float64
    assert np.isfinite(distances).all()
    np.testing.assert_allclose(distances, expected, atol=1e-12, rtol=0.0)
    np.testing.assert_allclose(distances[-1], 1.0, atol=1e-12)


def test_chamfer_distance_batch_matches_scalar_metric() -> None:
    generated, targets = _contours()
    distances = chamfer_distance_batch(generated, targets)
    expected = np.array([chamfer_distance(generated[i], targets[i]) for i in range(len(generated))])
    assert distances.dtype == np.float64
    assert np.isfinite(distances).all()
    np.testing.assert_allclose(distances, expected, atol=1e-12, rtol=0.0)
