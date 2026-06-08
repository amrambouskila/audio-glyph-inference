"""Tests for src/simulation/lookup_ratio.py."""

from __future__ import annotations

import numpy as np
import pytest
from src.simulation.lookup_ratio import align_to_reference, lookup_ratio

N_POINTS = 32


def _ellipse(y_scale: float) -> np.ndarray:
    t = 2.0 * np.pi * np.arange(N_POINTS) / N_POINTS
    return np.stack([0.5 * np.cos(t), y_scale * np.sin(t)], axis=1).astype(np.float64)


def test_lookup_ratio_fires_for_per_letter_constants() -> None:
    generated = np.stack([_ellipse(0.2), _ellipse(0.2), _ellipse(0.4), _ellipse(0.4)])
    np.testing.assert_allclose(lookup_ratio(generated, ["a", "a", "b", "b"]), 0.0, atol=1e-12)
    assert np.isinf(lookup_ratio(generated[:2], ["a", "a"]))


def test_lookup_ratio_validates_input_shape_and_labels() -> None:
    generated = np.stack([_ellipse(0.2), _ellipse(0.3)])
    with pytest.raises(ValueError, match="shape"):
        lookup_ratio(generated[:, :, 0], ["a", "b"])
    with pytest.raises(ValueError, match="matching length"):
        lookup_ratio(generated, ["a"])


def test_align_to_reference_handles_rotation_reflection_and_degenerate() -> None:
    target = _ellipse(0.3)
    rotated = target @ np.array([[0.0, -1.0], [1.0, 0.0]])
    reflected = target * np.array([-1.0, 1.0])
    assert align_to_reference(rotated, target).shape == target.shape
    assert np.isfinite(align_to_reference(reflected, target)).all()
    np.testing.assert_allclose(align_to_reference(np.zeros_like(target), target), 0.0, atol=1e-12)
