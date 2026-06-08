"""Anti-lookup contour-variance diagnostic shared by search and probe code."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

_ALIGN_EPS = 1e-12


def lookup_ratio(generated: np.ndarray, letters: Sequence[str]) -> float:
    """Compute within-letter / between-letter variance after Procrustes-style alignment.

    Args:
        generated: ndarray (B, N, 2) dtype=float64, generated contours in unit-square coordinates.
        letters: length-B letter labels corresponding to generated rows.

    Returns:
        Scalar float diagnostic; 0 means per-letter constant output, inf means no between-letter variance.
    """
    if generated.ndim != 3 or generated.shape[2] != 2:
        raise ValueError("generated must have shape (B, N, 2)")
    if generated.shape[0] != len(letters):
        raise ValueError("generated and letters must have matching length B")
    aligned_means = []
    within_values = []
    for letter in sorted(set(letters)):
        indices = [index for index, value in enumerate(letters) if value == letter]
        reference = generated[indices[0]]
        aligned = np.stack([align_to_reference(generated[index], reference) for index in indices])
        letter_mean = aligned.mean(axis=0)
        aligned_means.append(letter_mean)
        within_values.append(float(((aligned - letter_mean) ** 2).mean()))
    means = np.stack(aligned_means)
    global_mean = means.mean(axis=0)
    between = float(((means - global_mean) ** 2).mean())
    if between < _ALIGN_EPS:
        return float("inf")
    return float(np.mean(within_values) / between)


def align_to_reference(contour: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Align one contour to a reference with reflection-disabled similarity normalization.

    Args:
        contour: ndarray (N, 2) dtype=float64, generated contour in unit-square coordinates.
        reference: ndarray (N, 2) dtype=float64, reference contour in unit-square coordinates.

    Returns:
        ndarray (N, 2) dtype=float64, centered and similarity-aligned contour.
    """
    source = contour - contour.mean(axis=0)
    target = reference - reference.mean(axis=0)
    source_norm = float(np.linalg.norm(source))
    target_norm = float(np.linalg.norm(target))
    if source_norm < _ALIGN_EPS or target_norm < _ALIGN_EPS:
        return np.zeros_like(contour, dtype=np.float64)
    source = source / source_norm
    target = target / target_norm
    u, _, vt = np.linalg.svd(source.T @ target)
    rotation = u @ vt
    if np.linalg.det(rotation) < 0.0:
        u[:, -1] *= -1.0
        rotation = u @ vt
    return (source @ rotation).astype(np.float64)
