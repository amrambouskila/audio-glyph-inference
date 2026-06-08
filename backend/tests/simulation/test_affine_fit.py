"""Tests for src/simulation/affine_fit.py."""

from __future__ import annotations

import numpy as np
from src.simulation.affine_fit import _rank_factor, _ridge_affine, fit_fourier_theta, fit_lissajous_theta
from src.simulation.batch_synthesis import synthesize_fourier_batch, synthesize_lissajous_batch
from src.simulation.transforms.fourier_series import FourierSeriesFamily, _synthesize
from src.simulation.transforms.lissajous import LissajousFamily

N_POINTS = 64


def test_ridge_affine_lstsq_branch_recovers_known_map() -> None:
    phi = np.array([[0.0], [1.0], [2.0]], dtype=np.float64)
    outputs = np.array([[1.0, -1.0], [3.0, 0.0], [5.0, 1.0]], dtype=np.float64)
    matrix, bias = _ridge_affine(phi, outputs, alpha=0.0)
    np.testing.assert_allclose(matrix, [[2.0, 1.0]], atol=1e-12)
    np.testing.assert_allclose(bias, [1.0, -1.0], atol=1e-12)


def test_ridge_affine_regularized_branch_returns_finite_shapes() -> None:
    phi = np.array([[0.0], [1.0], [2.0]], dtype=np.float64)
    outputs = np.array([[1.0], [2.0], [3.0]], dtype=np.float64)
    matrix, bias = _ridge_affine(phi, outputs, alpha=0.5)
    assert matrix.shape == (1, 1)
    assert bias.shape == (1,)
    assert np.isfinite(matrix).all()
    assert np.isfinite(bias).all()


def test_rank_factor_identity_for_exact_rank() -> None:
    v = np.array([[1.0], [2.0], [-1.0]], dtype=np.float64)
    u_true = np.array([[0.5], [1.5]], dtype=np.float64)
    matrix = v @ u_true.T
    u, fitted_v = _rank_factor(matrix, rank=3)
    phi = np.array([[0.2, -0.1, 0.4], [1.0, 0.5, -0.25]], dtype=np.float64)
    np.testing.assert_allclose((phi @ fitted_v) @ u.T, phi @ matrix, atol=1e-12)


def test_fit_fourier_theta_recovers_constant_ellipse() -> None:
    phi = np.array([[0.0], [1.0], [2.0], [3.0]], dtype=np.float64)
    target = _synthesize(np.array([0.4, 0.0, 0.0, 0.2], dtype=np.float64), N_POINTS)
    target = target - target.mean(axis=0)
    target = target * (0.5 / np.abs(target).max())
    targets = np.repeat(target[None, :, :], phi.shape[0], axis=0)
    theta = fit_fourier_theta(phi, targets, {"rank_r": 1, "ridge_alpha": 0.0, "fourier_k": 1}, N_POINTS)
    method_theta = FourierSeriesFamily().fit_theta(
        phi, targets, {"rank_r": 1, "ridge_alpha": 0.0, "fourier_k": 1}, N_POINTS
    )
    assert set(theta) == {"rank_r", "ridge_alpha", "affine_u", "affine_v", "affine_b"}
    assert method_theta == theta
    synthesized = synthesize_fourier_batch(phi, theta, N_POINTS)
    np.testing.assert_allclose(synthesized, targets, atol=1e-10)


def test_fit_lissajous_theta_recovers_linear_ellipse() -> None:
    phi = np.array([[0.0], [1.0], [2.0], [3.0]], dtype=np.float64)
    target_theta = {
        "freq_ratio_a": 1,
        "freq_ratio_b": 1,
        "affine_w": [0.0, 0.0, 0.0],
        "affine_b": [0.0, 2.0, 1.0],
    }
    t = 2.0 * np.pi * np.arange(N_POINTS) / N_POINTS
    target = np.stack([2.0 * np.cos(t), np.sin(t)], axis=1)
    target = target - target.mean(axis=0)
    target = target * (0.5 / np.abs(target).max())
    targets = np.repeat(target[None, :, :], phi.shape[0], axis=0)
    theta = fit_lissajous_theta(phi, targets, {"freq_ratio_a": 1, "freq_ratio_b": 1}, N_POINTS)
    method_theta = LissajousFamily().fit_theta(phi, targets, {"freq_ratio_a": 1, "freq_ratio_b": 1}, N_POINTS)
    assert set(theta) == {"freq_ratio_a", "freq_ratio_b", "affine_w", "affine_b"}
    assert method_theta == theta
    synthesized = synthesize_lissajous_batch(phi, theta, N_POINTS)
    np.testing.assert_allclose(synthesized, targets, atol=1e-10)
    np.testing.assert_allclose(theta["affine_b"], [0.0, 0.5, 0.25], atol=1e-10)
    assert LissajousFamily().complexity(target_theta) == 2.0
