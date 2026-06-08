"""Normalize a single 2D contour into the canonical unit square.

Shared by the affine transform families (Fourier, Lissajous) whose synthesis
output lives at an arbitrary scale/offset and must land in [-0.5, 0.5] to match
the GlyphExtractor target convention. The eps floor keeps a degenerate
(collapsed) contour finite instead of dividing by zero. Pure NumPy.
"""

from __future__ import annotations

import numpy as np

_NORM_EPS = 1e-12


def normalize_to_unit_square(contour: np.ndarray) -> np.ndarray:
    """Centroid-center then scale by 0.5/max-abs into [-0.5, 0.5].

    Args:
        contour: ndarray (n, 2) float64 raw synthesized coordinates.

    Returns:
        ndarray (n, 2) float64 in [-0.5, 0.5], centroid at origin. A contour whose
        extent is below the eps floor collapses toward the origin (never raises).
    """
    centered = contour - contour.mean(axis=0)
    scale = 0.5 / max(float(np.abs(centered).max()), _NORM_EPS)
    return centered * scale
