"""Tests for src/simulation/transforms/phase_space_embedding.py — closed-form reference checks."""

from __future__ import annotations

import math

import numpy as np
from src.simulation.transforms.parameter_spec import ParameterSpec
from src.simulation.transforms.phase_space_embedding import (
    PhaseSpaceEmbeddingFamily,
    _embed,
    _reconstruct_signal,
    _rigid,
    _standardize,
)

SR = 16_000
FRAME = 512
HOP = 128
N_POINTS = 256


def _frames(signal: np.ndarray) -> np.ndarray:
    count = 1 + (len(signal) - FRAME) // HOP
    return np.stack([signal[i * HOP : i * HOP + FRAME] for i in range(count)]).astype(np.float64)


def test_name_is_phase_space_embedding() -> None:
    assert PhaseSpaceEmbeddingFamily().name() == "phase_space_embedding"


def test_parameter_space_has_five_placement_knobs() -> None:
    ps = PhaseSpaceEmbeddingFamily().parameter_space()
    assert set(ps) == {"tau", "gain", "rotation", "center_x", "center_y"}
    assert ps["tau"] == ParameterSpec(kind="integer", low=1, high=64)
    assert ps["rotation"].low == -math.pi
    assert ps["rotation"].high == math.pi


def test_reconstruct_signal_length_multiframe() -> None:
    out = _reconstruct_signal(np.zeros((4, FRAME)), HOP)
    assert out.shape == ((4 - 1) * HOP + FRAME,)


def test_reconstruct_signal_concatenates_hops_then_tail() -> None:
    frames = np.array([np.full(FRAME, float(i)) for i in range(4)])
    out = _reconstruct_signal(frames, HOP)
    np.testing.assert_array_equal(out[:HOP], 0.0)
    np.testing.assert_array_equal(out[HOP : 2 * HOP], 1.0)
    np.testing.assert_array_equal(out[2 * HOP : 3 * HOP], 2.0)
    np.testing.assert_array_equal(out[3 * HOP :], 3.0)


def test_reconstruct_signal_single_frame_is_identity() -> None:
    frame = np.arange(FRAME, dtype=np.float64).reshape(1, FRAME)
    np.testing.assert_array_equal(_reconstruct_signal(frame, HOP), np.arange(FRAME, dtype=np.float64))


def test_standardize_zero_mean_unit_variance() -> None:
    out = _standardize(np.random.default_rng(0).standard_normal(2000))
    np.testing.assert_allclose(out.mean(), 0.0, atol=1e-12)
    np.testing.assert_allclose(out.std(), 1.0, atol=1e-12)


def test_standardize_constant_signal_is_mean_removed() -> None:
    np.testing.assert_allclose(_standardize(np.full(16, 5.0)), 0.0, atol=1e-12)


def test_embedding_axis_ratio_at_omega_tau_pi_over_3() -> None:
    # ellipse axis-eigenvalue ratio = (1-|cos wt|)/(1+|cos wt|); at wt=pi/3 this is tan^2(pi/6)=1/3.
    omega, tau, periods = math.pi / 3.0, 1, 1000
    signal = np.sin(omega * np.arange(tau + 6 * periods))
    eigenvalues = np.linalg.eigvalsh(np.cov(_embed(signal, tau).T))
    np.testing.assert_allclose(eigenvalues[0] / eigenvalues[1], math.tan(math.pi / 6.0) ** 2, atol=1e-6)


def test_rigid_gain_is_linear() -> None:
    points = np.random.default_rng(1).standard_normal((10, 2))
    np.testing.assert_allclose(
        _rigid(points, 2.0, 0.3, np.zeros(2)), 2.0 * _rigid(points, 1.0, 0.3, np.zeros(2)), atol=1e-12
    )


def test_rigid_quarter_turn_maps_x_axis_to_y_axis() -> None:
    points = np.array([[1.0, 0.0], [2.0, 0.0], [3.0, 0.0]])
    np.testing.assert_allclose(
        _rigid(points, 1.0, math.pi / 2.0, np.zeros(2)), [[0.0, 1.0], [0.0, 2.0], [0.0, 3.0]], atol=1e-12
    )


def test_rigid_center_translates() -> None:
    points = np.random.default_rng(2).standard_normal((5, 2))
    center = np.array([0.3, -0.2])
    np.testing.assert_allclose(_rigid(points, 1.0, 0.0, center), points - center, atol=1e-12)


def test_forward_shape_dtype_range() -> None:
    frames = _frames(0.5 * np.sin(2.0 * np.pi * 440.0 * np.arange(SR) / SR))
    theta = {"tau": 8, "gain": 1.0, "rotation": 0.3, "center_x": 0.0, "center_y": 0.0}
    contour = PhaseSpaceEmbeddingFamily().forward(frames, theta)
    assert contour.shape == (N_POINTS, 2)
    assert contour.dtype == np.float64
    assert np.all(contour >= -0.5 - 1e-9) and np.all(contour <= 0.5 + 1e-9)


def test_forward_is_deterministic() -> None:
    frames = _frames(0.5 * np.sin(2.0 * np.pi * 440.0 * np.arange(SR) / SR))
    theta = {"tau": 8, "gain": 1.0, "rotation": 0.3, "center_x": 0.0, "center_y": 0.0}
    np.testing.assert_array_equal(
        PhaseSpaceEmbeddingFamily().forward(frames, theta), PhaseSpaceEmbeddingFamily().forward(frames, theta)
    )


def test_forward_all_zero_audio_collapses_without_error() -> None:
    theta = {"tau": 5, "gain": 1.0, "rotation": 0.5, "center_x": 0.2, "center_y": -0.1}
    contour = PhaseSpaceEmbeddingFamily().forward(np.zeros((10, FRAME)), theta)
    assert contour.shape == (N_POINTS, 2)
    assert np.all(np.isfinite(contour))
    assert np.all(contour >= -0.5 - 1e-9) and np.all(contour <= 0.5 + 1e-9)
    np.testing.assert_allclose(contour - contour[0], 0.0, atol=1e-12)


def test_complexity_closed_form() -> None:
    theta = {"tau": 7, "gain": 1.0, "rotation": 0.0, "center_x": 0.0, "center_y": 0.0}
    # len(parameter_space)=5 + log2(1+7)=log2(8)=3 -> 8.
    np.testing.assert_allclose(PhaseSpaceEmbeddingFamily().complexity(theta), 8.0, atol=1e-9)
