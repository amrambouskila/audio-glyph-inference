"""Shape distance metrics: d(F_θ(x_i), L_i).

All metrics take two ndarrays of shape (N, 2), dtype=float64, in unit-square
coordinates [-0.5, 0.5], and return a single non-negative float in ~[0, 1]:
lower is better, 0.0 == identical shapes. Chamfer and Fréchet are normalized by
the unit-square diagonal (SQRT2) so the three are comparable on one scale.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from src.constants import SQRT2

# Returned when a contour collapses to a point (zero spatial extent).
_DEGENERATE_PENALTY = 1.0
_NORM_FLOOR = 1e-12


def procrustes_distance(generated: np.ndarray, target: np.ndarray) -> float:
    """Full-Procrustes disparity after optimal similarity alignment.

    Translation/scale/rotation invariant; reflection is DISABLED (Hebrew letters
    are chiral). Point-correspondence (row i ↔ row i). Returns 1 - tr² in [0, 1].
    """
    a = generated - generated.mean(axis=0)
    b = target - target.mean(axis=0)
    a_norm = float(np.linalg.norm(a))
    b_norm = float(np.linalg.norm(b))
    if a_norm < _NORM_FLOOR or b_norm < _NORM_FLOOR:
        return _DEGENERATE_PENALTY
    a = a / a_norm
    b = b / b_norm
    _, singular_values, _ = np.linalg.svd(a.T @ b)
    reflection = float(np.sign(np.linalg.det(b.T @ a)))
    trace = singular_values[0] + reflection * singular_values[1]
    return float(min(max(1.0 - trace * trace, 0.0), 1.0))


def chamfer_distance(generated: np.ndarray, target: np.ndarray) -> float:
    """Symmetric mean nearest-neighbour distance, normalized by the unit-square diagonal."""
    gen_to_tgt, _ = cKDTree(target).query(generated)
    tgt_to_gen, _ = cKDTree(generated).query(target)
    raw = 0.5 * (float(gen_to_tgt.mean()) + float(tgt_to_gen.mean()))
    return raw / SQRT2


def frechet_distance(generated: np.ndarray, target: np.ndarray, *, cyclic_shifts: int = 16) -> float:
    """Discrete Fréchet distance, minimized over cyclic start-shifts + winding reversal, normalized.

    The minimization makes the metric measure shape rather than parameterization phase
    (master plan §5 / decision #7). cyclic_shifts=N gives the exact (all-shift) result;
    smaller values trade accuracy for speed. Report-only tiebreaker — not the search fitness.
    """
    n = len(generated)
    shifts = np.unique(np.linspace(0, n, num=min(cyclic_shifts, n), endpoint=False).astype(int))
    best = np.inf
    for oriented in (generated, generated[::-1]):
        for shift in shifts:
            best = min(best, _discrete_frechet(np.roll(oriented, -int(shift), axis=0), target))
    return float(best) / SQRT2


def _discrete_frechet(p: np.ndarray, q: np.ndarray) -> float:
    """Eiter-Mannila discrete Fréchet via iterative DP (no recursion; report-only path)."""
    n, m = len(p), len(q)
    ca = np.empty((n, m), dtype=np.float64)
    ca[0, 0] = float(np.hypot(*(p[0] - q[0])))
    for i in range(1, n):
        ca[i, 0] = max(ca[i - 1, 0], float(np.hypot(*(p[i] - q[0]))))
    for j in range(1, m):
        ca[0, j] = max(ca[0, j - 1], float(np.hypot(*(p[0] - q[j]))))
    for i in range(1, n):
        for j in range(1, m):
            ca[i, j] = max(min(ca[i - 1, j], ca[i - 1, j - 1], ca[i, j - 1]), float(np.hypot(*(p[i] - q[j]))))
    return float(ca[n - 1, m - 1])
