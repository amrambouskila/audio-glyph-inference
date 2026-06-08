"""Closed-form affine theta fitting for Phase-2 affine transform families."""

from __future__ import annotations

import numpy as np

from src.simulation.transforms.transform_base import Theta


def _fourier_basis(num_points: int, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Closed trig-polynomial bases. Returns two ndarrays (N, K) dtype=float64."""
    t = 2.0 * np.pi * np.arange(num_points) / num_points
    angles = np.outer(t, np.arange(1, k + 1))
    return np.cos(angles), np.sin(angles)


def _ridge_affine(phi: np.ndarray, outputs: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    """Fit outputs = phi @ M + b by ridge least squares.

    Args:
        phi: ndarray (B, D) dtype=float64, audio feature vectors.
        outputs: ndarray (B, C) dtype=float64, target coefficient/driver rows.
        alpha: non-negative ridge regularization weight.

    Returns:
        (M, b) where M is ndarray (D, C) float64 and b is ndarray (C,) float64.
    """
    phi_aug = np.concatenate([phi, np.ones((phi.shape[0], 1), dtype=np.float64)], axis=1)
    if alpha == 0.0:
        fitted = np.linalg.lstsq(phi_aug, outputs, rcond=None)[0]
        return fitted[:-1].astype(np.float64), fitted[-1].astype(np.float64)
    system = phi_aug.T @ phi_aug + alpha * np.eye(phi_aug.shape[1], dtype=np.float64)
    fitted = np.linalg.solve(system, phi_aug.T @ outputs)
    return fitted[:-1].astype(np.float64), fitted[-1].astype(np.float64)


def _rank_factor(matrix: np.ndarray, rank: int) -> tuple[np.ndarray, np.ndarray]:
    """Factor a D-by-C affine matrix so phi @ M == (phi @ V) @ U.T at rank r.

    Args:
        matrix: ndarray (D, C) dtype=float64, full affine matrix.
        rank: requested low rank r.

    Returns:
        (U, V), where U is ndarray (C, r) float64 and V is ndarray (D, r) float64.
    """
    left, singular_values, right_t = np.linalg.svd(matrix, full_matrices=False)
    r = min(rank, singular_values.size)
    v = left[:, :r]
    u = right_t[:r, :].T * singular_values[:r]
    return u.astype(np.float64), v.astype(np.float64)


def fit_fourier_theta(phi: np.ndarray, targets: np.ndarray, searched_theta: Theta, num_points: int) -> Theta:
    """Fit Fourier affine theta from features to target contours.

    Args:
        phi: ndarray (B, D) dtype=float64, audio feature vectors.
        targets: ndarray (B, N, 2) dtype=float64, unit-square target contours.
        searched_theta: theta with rank_r, ridge_alpha, and optional fourier_k.
        num_points: contour point count N.

    Returns:
        theta with affine_u, affine_v, and affine_b lists added.
    """
    k = int(searched_theta["fourier_k"])
    cos, sin = _fourier_basis(num_points, k)
    zeros = np.zeros_like(cos)
    basis = np.block([[cos, sin, zeros, zeros], [zeros, zeros, cos, sin]])
    flattened_targets = np.concatenate([targets[:, :, 0], targets[:, :, 1]], axis=1)
    coeffs = np.linalg.lstsq(basis, flattened_targets.T, rcond=None)[0].T
    matrix, bias = _ridge_affine(phi, coeffs, float(searched_theta["ridge_alpha"]))
    u, v = _rank_factor(matrix, int(searched_theta["rank_r"]))
    theta = dict(searched_theta)
    theta.pop("fourier_k", None)
    theta["affine_u"] = u.reshape(-1).tolist()
    theta["affine_v"] = v.reshape(-1).tolist()
    theta["affine_b"] = bias.tolist()
    return theta


def fit_lissajous_theta(phi: np.ndarray, targets: np.ndarray, searched_theta: Theta, num_points: int) -> Theta:
    """Fit linear-form Lissajous affine theta from features to target contours.

    Args:
        phi: ndarray (B, D) dtype=float64, audio feature vectors.
        targets: ndarray (B, N, 2) dtype=float64, unit-square target contours.
        searched_theta: theta with freq_ratio_a and freq_ratio_b.
        num_points: contour point count N.

    Returns:
        theta with affine_w and affine_b lists added.
    """
    t = 2.0 * np.pi * np.arange(num_points) / num_points
    a = int(searched_theta["freq_ratio_a"])
    b = int(searched_theta["freq_ratio_b"])
    zeros = np.zeros(num_points, dtype=np.float64)
    basis = np.stack(
        [
            np.concatenate([np.sin(a * t), zeros]),
            np.concatenate([np.cos(a * t), zeros]),
            np.concatenate([zeros, np.sin(b * t)]),
        ],
        axis=1,
    )
    flattened_targets = np.concatenate([targets[:, :, 0], targets[:, :, 1]], axis=1)
    drivers = np.linalg.lstsq(basis, flattened_targets.T, rcond=None)[0].T
    matrix, bias = _ridge_affine(phi, drivers, alpha=0.0)
    theta = dict(searched_theta)
    theta["affine_w"] = matrix.T.reshape(-1).tolist()
    theta["affine_b"] = bias.tolist()
    return theta
