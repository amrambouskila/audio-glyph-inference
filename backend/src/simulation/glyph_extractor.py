"""Glyph extraction: STAM-style font glyph -> ordered 2D contour.

Uses freetype-py to render a letter at a fixed raster size, then traces
the outer contour with OpenCV, resamples to a fixed number of points for
cross-letter comparability, and returns coordinates normalized to a
unit square centered at the origin.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


class GlyphExtractor:
    """Standalone glyph rasterizer + contour resampler."""

    def __init__(
        self,
        font_path: Path,
        raster_size_px: int,
        num_contour_points: int,
    ) -> None:
        raise NotImplementedError

    def extract(self, letter: str) -> np.ndarray:
        """Return the target contour for a letter.

        Args:
            letter: one of constants.HEBREW_LETTERS.

        Returns:
            ndarray of shape (num_contour_points, 2), dtype=float64,
            units=unit-square coordinates in [-0.5, 0.5].
        """
        raise NotImplementedError
