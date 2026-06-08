"""Batched shape-distance helpers for SearchEngine candidate scoring."""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from src.constants import SQRT2

_DEGENERATE_PENALTY = 1.0
_NORM_FLOOR = 1e-12


def procrustes_distance_batch(generated: np.ndarray, targets: np.ndarray) -> np.ndarray:
    """Batched reflection-disabled Procrustes disparity.

    Args:
        generated: ndarray (B, N, 2) dtype=float64, generated contours in unit-square coordinates.
        targets: ndarray (B, N, 2) dtype=float64, target contours in unit-square coordinates.

    Returns:
        ndarray (B,) dtype=float64, one normalized distance per row.
    """
    gen_centered = generated - generated.mean(axis=1, keepdims=True)
    tgt_centered = targets - targets.mean(axis=1, keepdims=True)
    gen_norm = np.sqrt((gen_centered**2).sum(axis=(1, 2)))
    tgt_norm = np.sqrt((tgt_centered**2).sum(axis=(1, 2)))
    degenerate = (gen_norm < _NORM_FLOOR) | (tgt_norm < _NORM_FLOOR)
    safe_gen = np.where(degenerate, 1.0, gen_norm)[:, None, None]
    safe_tgt = np.where(degenerate, 1.0, tgt_norm)[:, None, None]
    gen_normalized = gen_centered / safe_gen
    tgt_normalized = tgt_centered / safe_tgt
    cov = np.einsum("bni,bnj->bij", gen_normalized, tgt_normalized)
    singular_values = np.linalg.svd(cov, compute_uv=False)
    tgt_to_gen = np.einsum("bni,bnj->bij", tgt_normalized, gen_normalized)
    reflection = np.sign(np.linalg.det(tgt_to_gen))
    trace = singular_values[:, 0] + reflection * singular_values[:, 1]
    disparity = np.clip(1.0 - trace * trace, 0.0, 1.0)
    return np.where(degenerate, _DEGENERATE_PENALTY, disparity).astype(np.float64)


def chamfer_distance_batch(generated: np.ndarray, targets: np.ndarray) -> np.ndarray:
    """Batched symmetric Chamfer via independent KD-tree row queries.

    Args:
        generated: ndarray (B, N, 2) dtype=float64, generated contours in unit-square coordinates.
        targets: ndarray (B, N, 2) dtype=float64, target contours in unit-square coordinates.

    Returns:
        ndarray (B,) dtype=float64, one normalized distance per row.
    """
    distances = [
        0.5
        * (
            float(cKDTree(target).query(generated_row)[0].mean())
            + float(cKDTree(generated_row).query(target)[0].mean())
        )
        / SQRT2
        for generated_row, target in zip(generated, targets, strict=True)
    ]
    return np.asarray(distances, dtype=np.float64)
