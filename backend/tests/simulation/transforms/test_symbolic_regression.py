"""Tests for src/simulation/transforms/symbolic_regression.py."""

from __future__ import annotations

import math

import numpy as np
import pytest
from src.simulation.transforms.parameter_spec import ParameterSpec
from src.simulation.transforms.symbolic_regression import SymbolicRegressionFamily, _coefficient_expressions

SR = 16_000
FRAME = 512
HOP = 128
N_POINTS = 256


def _frames(signal: np.ndarray) -> np.ndarray:
    count = 1 + (len(signal) - FRAME) // HOP
    return np.stack([signal[i * HOP : i * HOP + FRAME] for i in range(count)]).astype(np.float64)


def _tone(freq_hz: float, duration_s: float = 1.0) -> np.ndarray:
    t = np.arange(int(SR * duration_s)) / SR
    return 0.5 * np.sin(2.0 * np.pi * freq_hz * t)


def _ellipse_theta() -> dict:
    return {
        "fourier_k": 1,
        "coeff_0": "0.4",
        "coeff_1": "0.0",
        "coeff_2": "0.0",
        "coeff_3": "0.2",
    }


def test_name_is_symbolic_regression() -> None:
    assert SymbolicRegressionFamily().name() == "symbolic_regression"


def test_parameter_space_has_no_generic_search_knobs() -> None:
    assert SymbolicRegressionFamily().parameter_space() == {}
    assert isinstance(ParameterSpec(kind="continuous", low=0.0, high=1.0), ParameterSpec)


def test_forward_exact_expression_ellipse_is_orientation_pinned() -> None:
    contour = SymbolicRegressionFamily().forward(_frames(_tone(1000.0)), _ellipse_theta())
    assert contour.shape == (N_POINTS, 2)
    assert contour.dtype == np.float64
    assert np.all(contour >= -0.5 - 1e-9) and np.all(contour <= 0.5 + 1e-9)
    np.testing.assert_allclose(contour[0], [0.5, 0.0], atol=1e-9)
    np.testing.assert_allclose(contour[N_POINTS // 4], [0.0, 0.25], atol=1e-9)


def test_forward_uses_audio_features() -> None:
    theta = {
        "fourier_k": 1,
        "coeff_0": "0.4 + 1e-4 * f0",
        "coeff_1": "0.0",
        "coeff_2": "0.0",
        "coeff_3": "0.2",
    }
    low = SymbolicRegressionFamily().forward(_frames(_tone(400.0)), theta)
    high = SymbolicRegressionFamily().forward(_frames(_tone(3000.0)), theta)
    assert not np.allclose(low, high)


def test_forward_is_deterministic() -> None:
    frames = _frames(_tone(1000.0))
    theta = _ellipse_theta()
    np.testing.assert_array_equal(
        SymbolicRegressionFamily().forward(frames, theta), SymbolicRegressionFamily().forward(frames, theta)
    )


def test_complexity_closed_form() -> None:
    theta = _ellipse_theta()
    expected_expression_cost = sum(math.log2(1.0 + len(str(theta[f"coeff_{index}"]))) for index in range(4))
    expected = 4.0 + 5.0 + 1.0 + expected_expression_cost
    np.testing.assert_allclose(SymbolicRegressionFamily().complexity(theta), expected, atol=1e-12)


@pytest.mark.parametrize(
    "theta",
    [
        {},
        {"fourier_k": 0},
        {"fourier_k": 1, "coeff_0": "0", "coeff_1": "0", "coeff_2": "0"},
        {"fourier_k": 1, "coeff_0": 0.0, "coeff_1": "0", "coeff_2": "0", "coeff_3": "0"},
    ],
)
def test_coefficient_expressions_rejects_malformed_theta(theta: dict) -> None:
    with pytest.raises(ValueError):
        _coefficient_expressions(theta)
