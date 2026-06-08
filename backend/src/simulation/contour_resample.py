"""Arc-length-uniform resampling of a closed polyline.

Shared by the glyph extractor (resampling cv2 stroke boundaries) and the
phase-space transform family (resampling a delay-embedding trajectory) so the
two never drift. Pure NumPy; no config, no state.
"""

from __future__ import annotations

import numpy as np


def resample_closed(points: np.ndarray, n: int) -> np.ndarray:
    """Resample a closed polyline to n arc-length-uniform points.

    Args:
        points: ndarray (m, 2) float64 ordered vertices of a closed polyline (m >= 2).
        n: number of output points.

    Returns:
        ndarray (n, 2) float64 vertices spaced uniformly by arc length around the loop.
    """
    deltas = np.roll(points, -1, axis=0) - points
    seg_len = np.hypot(deltas[:, 0], deltas[:, 1])
    cumulative = np.concatenate([[0.0], np.cumsum(seg_len)])
    targets = np.linspace(0.0, cumulative[-1], n, endpoint=False)
    idx = np.clip(np.searchsorted(cumulative, targets, side="right") - 1, 0, len(points) - 1)
    seg_frac = (targets - cumulative[idx]) / seg_len[idx]
    return points[idx] + seg_frac[:, None] * deltas[idx]
