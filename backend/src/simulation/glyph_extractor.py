"""Glyph extraction: STAM-style font glyph -> ordered list of 2D contours.

Renders a letter with freetype-py and traces every external stroke with
OpenCV. Letters with detached strokes (e.g. ה, ק in this STAM font) yield
more than one contour; they are returned as an ordered list (largest first)
so no ink is dropped. Each contour is arc-length-resampled (points allocated
by perimeter share of a fixed total budget) and all contours are normalized
jointly to a unit square centered at the origin (y-up), preserving the
relative position and scale of the strokes.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import freetype
import numpy as np

from src.simulation.contour_resample import resample_closed

# Fraction of the raster the rendered glyph fills, leaving margin so the
# tallest letter (lamed) cannot clip the canvas before contouring. Rendering
# coefficient, not a domain value.
_RENDER_FILL_FRACTION = 0.65
# Grayscale -> binary threshold for the anti-aliased glyph bitmap (0-255).
_BINARIZE_THRESHOLD = 127
# Floor on points per stroke so a small detached stroke is still a usable polygon.
_MIN_POINTS_PER_CONTOUR = 8


class GlyphExtractor:
    """Standalone glyph rasterizer + multi-contour resampler."""

    def __init__(self, font_path: Path, raster_size_px: int, num_contour_points: int) -> None:
        self._face = freetype.Face(str(font_path))
        self._raster_size_px = raster_size_px
        self._num_contour_points = num_contour_points
        self._face.set_pixel_sizes(0, int(raster_size_px * _RENDER_FILL_FRACTION))

    def extract(self, letter: str) -> list[np.ndarray]:
        """Return the target stroke contours for a letter.

        Args:
            letter: one of constants.GLYPH_FORMS.

        Returns:
            ordered list (largest stroke first) of ndarray, each shape (n_i, 2),
            dtype=float64, units=unit-square coordinates in [-0.5, 0.5], y-up,
            jointly centered at the glyph centroid. Sum of n_i ≈ num_contour_points.
        """
        raster = self._render(letter)
        contours = self._external_contours(raster)
        resampled = self._resample_by_perimeter(contours, self._num_contour_points)
        return self._normalize_joint(resampled)

    def _render(self, letter: str) -> np.ndarray:
        """Render a letter into a (raster, raster) uint8 canvas, glyph centered."""
        self._face.load_char(letter, freetype.FT_LOAD_RENDER)
        bitmap = self._face.glyph.bitmap
        rows, width, pitch = bitmap.rows, bitmap.width, bitmap.pitch
        glyph = np.array(bitmap.buffer, dtype=np.uint8).reshape(rows, pitch)[:, :width]
        canvas = np.zeros((self._raster_size_px, self._raster_size_px), dtype=np.uint8)
        top = (self._raster_size_px - rows) // 2
        left = (self._raster_size_px - width) // 2
        canvas[top : top + rows, left : left + width] = glyph
        return canvas

    def _external_contours(self, raster: np.ndarray) -> list[np.ndarray]:
        """All external stroke boundaries, ordered largest-area first."""
        _, binary = cv2.threshold(raster, _BINARIZE_THRESHOLD, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        ordered = sorted(contours, key=cv2.contourArea, reverse=True)
        return [c.reshape(-1, 2).astype(np.float64) for c in ordered]

    def _resample_by_perimeter(self, contours: list[np.ndarray], total: int) -> list[np.ndarray]:
        """Resample each closed contour, allocating `total` points by perimeter share."""
        perimeters = [self._perimeter(c) for c in contours]
        total_perimeter = sum(perimeters)
        counts = [max(_MIN_POINTS_PER_CONTOUR, round(total * p / total_perimeter)) for p in perimeters]
        return [resample_closed(c, n) for c, n in zip(contours, counts, strict=True)]

    @staticmethod
    def _perimeter(points: np.ndarray) -> float:
        deltas = np.roll(points, -1, axis=0) - points
        return float(np.hypot(deltas[:, 0], deltas[:, 1]).sum())

    @staticmethod
    def _normalize_joint(contours: list[np.ndarray]) -> list[np.ndarray]:
        """Center on the combined centroid, flip to y-up, scale jointly into [-0.5, 0.5]."""
        centroid = np.vstack(contours).mean(axis=0)
        centered = [c - centroid for c in contours]
        for contour in centered:
            contour[:, 1] *= -1.0  # image y is top-down; flip to math y-up
        scale = 0.5 / np.abs(np.vstack(centered)).max()
        return [c * scale for c in centered]
