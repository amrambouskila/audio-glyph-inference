"""Single contour-comparison dispatcher used by both the search engine and /api/inference."""

from __future__ import annotations

import numpy as np

from src.simulation.shape_distance import chamfer_distance, frechet_distance, procrustes_distance

_METRICS = {
    "procrustes": procrustes_distance,
    "frechet": frechet_distance,
    "chamfer": chamfer_distance,
}


def contour_compare(generated: np.ndarray, target: np.ndarray, metric: str) -> float:
    """Distance between two (N, 2) contours under the named metric (procrustes | frechet | chamfer)."""
    try:
        distance_fn = _METRICS[metric]
    except KeyError as exc:
        raise ValueError(f"unknown metric {metric!r}; expected one of {sorted(_METRICS)}") from exc
    return distance_fn(generated, target)
