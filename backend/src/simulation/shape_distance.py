"""Shape distance metrics: d(F_θ(x_i), L_i).

All metrics take two ndarrays of shape (N, 2), dtype=float64, in unit-
square coordinates, and return a single float. Rotation/translation/
scale invariance is the default (Procrustes alignment before distance).
"""
from __future__ import annotations

import numpy as np


def procrustes_distance(generated: np.ndarray, target: np.ndarray) -> float:
    """Full Procrustes distance after optimal similarity alignment."""
    raise NotImplementedError


def frechet_distance(generated: np.ndarray, target: np.ndarray) -> float:
    """Discrete Fréchet distance — sensitive to ordering along the contour."""
    raise NotImplementedError


def chamfer_distance(generated: np.ndarray, target: np.ndarray) -> float:
    """Symmetric Chamfer distance — order-invariant."""
    raise NotImplementedError