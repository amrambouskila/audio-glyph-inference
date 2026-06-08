"""Tests for src/simulation/transforms/lissajous.py — closed-form reference checks."""

from __future__ import annotations

import numpy as np
from src.simulation.transforms.lissajous import LissajousFamily
from src.simulation.transforms.parameter_spec import ParameterSpec

SR = 16_000
FRAME = 512
HOP = 128
N_POINTS = 256
D = 8 + 4 + 4 * 3


def _frames(signal: np.ndarray) -> np.ndarray:
    count = 1 + (len(signal) - FRAME) // HOP
    return np.stack([signal[i * HOP : i * HOP + FRAME] for i in range(count)]).astype(np.float64)


def _tone(freq_hz: float, duration_s: float = 1.0) -> np.ndarray:
    t = np.arange(int(SR * duration_s)) / SR
    return 0.5 * np.sin(2.0 * np.pi * freq_hz * t)


def test_name_is_lissajous() -> None:
    assert LissajousFamily().name() == "lissajous"


def test_parameter_space_declares_frequency_ratios() -> None:
    ps = LissajousFamily().parameter_space()
    assert set(ps) == {"freq_ratio_a", "freq_ratio_b"}
    assert ps["freq_ratio_a"] == ParameterSpec(kind="integer", low=1, high=5)
    assert ps["freq_ratio_b"] == ParameterSpec(kind="integer", low=1, high=5)


def test_forward_ellipse_axis_ratio() -> None:
    # P=0,Q=2,R=1 is the linear form of delta=pi/2, A_x=2, A_y=1.
    theta = {"freq_ratio_a": 1, "freq_ratio_b": 1, "affine_w": [0.0] * (3 * D), "affine_b": [0.0, 2.0, 1.0]}
    contour = LissajousFamily().forward(_frames(_tone(1000.0)), theta)
    np.testing.assert_allclose(contour[0], [0.5, 0.0], atol=1e-9)
    np.testing.assert_allclose(contour[N_POINTS // 4], [0.0, 0.25], atol=1e-9)
    np.testing.assert_allclose(contour[N_POINTS // 2], [-0.5, 0.0], atol=1e-9)
    np.testing.assert_allclose(contour[3 * N_POINTS // 4], [0.0, -0.25], atol=1e-9)


def test_forward_degenerate_line_when_phase_zero() -> None:
    theta = {"freq_ratio_a": 1, "freq_ratio_b": 1, "affine_w": [0.0] * (3 * D), "affine_b": [1.0, 0.0, 1.0]}
    contour = LissajousFamily().forward(_frames(_tone(1000.0)), theta)
    np.testing.assert_allclose(contour[:, 0], contour[:, 1], atol=1e-12)


def test_forward_figure_eight_self_intersects_at_origin() -> None:
    theta = {"freq_ratio_a": 1, "freq_ratio_b": 2, "affine_w": [0.0] * (3 * D), "affine_b": [0.0, 1.0, 1.0]}
    contour = LissajousFamily().forward(_frames(_tone(1000.0)), theta)
    np.testing.assert_allclose(contour[N_POINTS // 4], contour[3 * N_POINTS // 4], atol=1e-9)
    np.testing.assert_allclose(contour[N_POINTS // 4], [0.0, 0.0], atol=1e-9)


def test_frequency_ratios_are_global_not_audio_driven() -> None:
    # affine_w = 0 -> drivers constant; identical contour for any audio proves a,b ignore phi.
    theta = {"freq_ratio_a": 2, "freq_ratio_b": 3, "affine_w": [0.0] * (3 * D), "affine_b": [0.5, 1.0, 0.7]}
    low = LissajousFamily().forward(_frames(_tone(300.0)), theta)
    high = LissajousFamily().forward(_frames(_tone(5000.0)), theta)
    np.testing.assert_array_equal(low, high)


def test_forward_shape_dtype_range() -> None:
    rng = np.random.default_rng(0)
    theta = {
        "freq_ratio_a": 2,
        "freq_ratio_b": 3,
        "affine_w": rng.standard_normal(3 * D).tolist(),
        "affine_b": rng.standard_normal(3).tolist(),
    }
    contour = LissajousFamily().forward(_frames(_tone(700.0)), theta)
    assert contour.shape == (N_POINTS, 2)
    assert contour.dtype == np.float64
    assert np.all(contour >= -0.5 - 1e-9) and np.all(contour <= 0.5 + 1e-9)


def test_forward_is_deterministic() -> None:
    rng = np.random.default_rng(1)
    frames = _frames(_tone(700.0))
    theta = {
        "freq_ratio_a": 2,
        "freq_ratio_b": 3,
        "affine_w": rng.standard_normal(3 * D).tolist(),
        "affine_b": rng.standard_normal(3).tolist(),
    }
    np.testing.assert_array_equal(LissajousFamily().forward(frames, theta), LissajousFamily().forward(frames, theta))


def test_complexity_closed_form() -> None:
    theta = {"freq_ratio_a": 1, "freq_ratio_b": 2, "affine_w": [0.0] * (3 * D), "affine_b": [0.0, 2.0, 1.0]}
    # nnz(affine) = 2 (affine_b), log2(1) = 0, log2(2) = 1 -> 3.
    np.testing.assert_allclose(LissajousFamily().complexity(theta), 3.0, atol=1e-9)
