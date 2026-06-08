"""Batched contour synthesis for affine transform families."""

from __future__ import annotations

import numpy as np

from src.simulation.transforms.fourier_series import _basis
from src.simulation.transforms.transform_base import Theta

_NORM_EPS = 1e-12
_LISSAJOUS_DRIVERS = 3


def _normalize_batch(raw: np.ndarray) -> np.ndarray:
    """Centroid-center and scale each row independently.

    Args:
        raw: ndarray (B, N, 2) dtype=float64, raw synthesized coordinates.

    Returns:
        ndarray (B, N, 2) dtype=float64 in [-0.5, 0.5].
    """
    centered = raw - raw.mean(axis=1, keepdims=True)
    max_abs = np.abs(centered).reshape(centered.shape[0], -1).max(axis=1)
    scale = 0.5 / np.maximum(max_abs, _NORM_EPS)
    return (centered * scale[:, None, None]).astype(np.float64)


def synthesize_fourier_batch(phi: np.ndarray, theta: Theta, num_points: int) -> np.ndarray:
    """Synthesize Fourier contours for a feature matrix.

    Args:
        phi: ndarray (B, D) dtype=float64, audio feature vectors.
        theta: Fourier theta with rank_r, affine_u, affine_v, affine_b.
        num_points: output contour point count N.

    Returns:
        ndarray (B, N, 2) dtype=float64 in [-0.5, 0.5].
    """
    rank_r = int(theta["rank_r"])
    affine_b = np.asarray(theta["affine_b"], dtype=np.float64)
    k = affine_b.size // 4
    u = np.asarray(theta["affine_u"], dtype=np.float64).reshape(4 * k, rank_r)
    v = np.asarray(theta["affine_v"], dtype=np.float64).reshape(phi.shape[1], rank_r)
    coeffs = (phi @ v) @ u.T + affine_b
    a, b, c, d = coeffs.reshape(phi.shape[0], 4, k).transpose(1, 0, 2)
    cos, sin = _basis(num_points, k)
    x = a @ cos.T + b @ sin.T
    y = c @ cos.T + d @ sin.T
    return _normalize_batch(np.stack([x, y], axis=2))


def synthesize_lissajous_batch(phi: np.ndarray, theta: Theta, num_points: int) -> np.ndarray:
    """Synthesize linear-form Lissajous contours for a feature matrix.

    Args:
        phi: ndarray (B, D) dtype=float64, audio feature vectors.
        theta: Lissajous theta with freq_ratio_a/freq_ratio_b, affine_w, affine_b.
        num_points: output contour point count N.

    Returns:
        ndarray (B, N, 2) dtype=float64 in [-0.5, 0.5].
    """
    w = np.asarray(theta["affine_w"], dtype=np.float64).reshape(_LISSAJOUS_DRIVERS, phi.shape[1])
    affine_b = np.asarray(theta["affine_b"], dtype=np.float64)
    p, q, r = (phi @ w.T + affine_b).T
    a = int(theta["freq_ratio_a"])
    b = int(theta["freq_ratio_b"])
    t = 2.0 * np.pi * np.arange(num_points) / num_points
    x = p[:, None] * np.sin(a * t)[None, :] + q[:, None] * np.cos(a * t)[None, :]
    y = r[:, None] * np.sin(b * t)[None, :]
    return _normalize_batch(np.stack([x, y], axis=2))
