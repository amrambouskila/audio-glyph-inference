"""GlyphTarget — canonical 2D target shape for a Hebrew letter.

Rendered from a STAM-style Torah font (backend/data/fonts/) via freetype,
then converted to an ordered contour of (x, y) points in a unit square.
See simulation/glyph_extractor.py for the rendering pipeline.
"""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class GlyphTarget(BaseModel):
    """Target 2D geometry for one Hebrew letter."""

    id: UUID
    letter: str = Field(
        description="One of the 22 Hebrew letters in constants.HEBREW_LETTERS.",
    )
    font_name: str = Field(
        description="Font file name (e.g., 'StamAshkenazCLM.ttf'); tracked for reproducibility.",
    )
    raster_size_px: int = Field(
        description="Square raster size used during rendering; see config.glyph_raster_size_px.",
    )
    contour_path: str = Field(
        description="Absolute path to the .npy file holding the (N, 2) contour, dtype=float64.",
    )
    num_points: int = Field(
        description="Number of points in the resampled contour.",
    )