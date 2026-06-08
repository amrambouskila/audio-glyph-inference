"""Tests for src/simulation/transforms/fourier_series.py — closed-form reference checks."""

from __future__ import annotations

import math

import numpy as np
from src.simulation.transforms.fourier_series import FourierSeriesFamily, _synthesize
from src.simulation.transforms.parameter_spec import ParameterSpec

SR = 16_000
FRAME = 512
HOP = 128
N_POINTS = 256
D = 8 + 4 + 4 * 3  # n_mels + global + per-segment descriptors


def _frames(signal: np.ndarray) -> np.ndarray:
    count = 1 + (len(signal) - FRAME) // HOP
    return np.stack([signal[i * HOP : i * HOP + FRAME] for i in range(count)]).astype(np.float64)


def _tone(freq_hz: float, duration_s: float = 1.0) -> np.ndarray:
    t = np.arange(int(SR * duration_s)) / SR
    return 0.5 * np.sin(2.0 * np.pi * freq_hz * t)


def _ellipse_theta(amp_a: float, amp_b: float) -> dict:
    # rank-1 affine with zero map -> coeffs == affine_b == (a1, b1, c1, d1) = (A, 0, 0, B).
    return {
        "rank_r": 1,
        "ridge_alpha": 0.1,
        "affine_u": [0.0] * 4,
        "affine_v": [0.0] * D,
        "affine_b": [amp_a, 0.0, 0.0, amp_b],
    }


def test_name_is_fourier_series() -> None:
    assert FourierSeriesFamily().name() == "fourier_series"


def test_parameter_space_declares_searched_knobs() -> None:
    ps = FourierSeriesFamily().parameter_space()
    assert set(ps) == {"rank_r", "ridge_alpha"}
    assert ps["rank_r"] == ParameterSpec(kind="integer", low=1, high=3)
    assert ps["ridge_alpha"].kind == "continuous"


def test_forward_exact_ellipse_is_orientation_pinned() -> None:
    amp_a, amp_b = 0.4, 0.2
    contour = FourierSeriesFamily().forward(_frames(_tone(1000.0)), _ellipse_theta(amp_a, amp_b))
    np.testing.assert_allclose(contour[0], [0.5, 0.0], atol=1e-9)
    np.testing.assert_allclose(contour[N_POINTS // 4], [0.0, 0.5 * amp_b / amp_a], atol=1e-9)


def test_synthesize_is_exactly_linear() -> None:
    rng = np.random.default_rng(0)
    coeffs_a = rng.standard_normal(8)  # 4K -> K = 2
    coeffs_b = rng.standard_normal(8)
    np.testing.assert_allclose(
        _synthesize(coeffs_a + coeffs_b, 64), _synthesize(coeffs_a, 64) + _synthesize(coeffs_b, 64), atol=1e-12
    )
    np.testing.assert_allclose(_synthesize(2.0 * coeffs_a, 64), 2.0 * _synthesize(coeffs_a, 64), atol=1e-12)


def test_forward_random_theta_fills_box() -> None:
    rng = np.random.default_rng(1)
    k, r = 2, 2
    theta = {
        "rank_r": r,
        "ridge_alpha": 0.5,
        "affine_u": rng.standard_normal(4 * k * r).tolist(),
        "affine_v": rng.standard_normal(D * r).tolist(),
        "affine_b": rng.standard_normal(4 * k).tolist(),
    }
    contour = FourierSeriesFamily().forward(_frames(_tone(800.0)), theta)
    assert contour.shape == (N_POINTS, 2)
    assert contour.dtype == np.float64
    assert np.all(contour >= -0.5 - 1e-9) and np.all(contour <= 0.5 + 1e-9)
    np.testing.assert_allclose(np.abs(contour).max(), 0.5, atol=1e-9)


def test_forward_varies_with_audio() -> None:
    rng = np.random.default_rng(2)
    theta = {
        "rank_r": 2,
        "ridge_alpha": 0.5,
        "affine_u": rng.standard_normal(8 * 2).tolist(),
        "affine_v": rng.standard_normal(D * 2).tolist(),
        "affine_b": rng.standard_normal(8).tolist(),
    }
    low = FourierSeriesFamily().forward(_frames(_tone(400.0)), theta)
    high = FourierSeriesFamily().forward(_frames(_tone(3000.0)), theta)
    assert not np.allclose(low, high)


def test_forward_is_deterministic() -> None:
    frames = _frames(_tone(1000.0))
    theta = _ellipse_theta(0.4, 0.2)
    np.testing.assert_array_equal(
        FourierSeriesFamily().forward(frames, theta), FourierSeriesFamily().forward(frames, theta)
    )


def test_forward_has_nonzero_signed_area() -> None:
    contour = FourierSeriesFamily().forward(_frames(_tone(1000.0)), _ellipse_theta(0.4, 0.2))
    x, y = contour[:, 0], contour[:, 1]
    area = 0.5 * abs(float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)))
    assert area > 1e-6


def test_complexity_closed_form() -> None:
    theta = _ellipse_theta(0.4, 0.2)
    # D=24, K=1, r=1: n_eff = 1*(4+24)+4 = 32; #keys = 5; order = 1*1 = 1.
    expected = 32.0 + 5.0 + (math.log2(1.4) + math.log2(1.2)) + 1.0
    np.testing.assert_allclose(FourierSeriesFamily().complexity(theta), expected, atol=1e-9)
