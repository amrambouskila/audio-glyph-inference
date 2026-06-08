"""GlyphTarget — canonical 2D target shape for a Hebrew letter.

Rendered from a STAM-style Torah font (backend/data/fonts/) via freetype,
then converted to an ordered contour of (x, y) points in a unit square.
See simulation/glyph_extractor.py for the rendering pipeline.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.constants import BASE_LETTER_BY_GLYPH_FORM, GLYPH_FORMS, HEBREW_LETTERS


class GlyphTarget(BaseModel):
    """Target 2D geometry for one Hebrew letter."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    letter: str = Field(
        description="Base letter: one of the 22 Hebrew letters in constants.HEBREW_LETTERS.",
    )
    glyph_form: str = Field(
        description="Rendered written form: a regular Hebrew letter or one of the five sofit forms.",
    )
    font_name: str = Field(
        description="Font file name (e.g., 'StamAshkenazCLM.ttf'); tracked for reproducibility.",
    )
    raster_size_px: int = Field(
        description="Square raster size used during rendering; see config.glyph_raster_size_px.",
    )
    contour_path: str = Field(
        description="Absolute path to the .npz holding the ordered (n_i, 2) float64 stroke contours.",
    )
    num_points: int = Field(
        description="Total number of resampled contour points across all strokes.",
    )
    num_contours: int = Field(
        description="Number of ordered stroke contours (1 for most letters; 2 for he/qof).",
    )

    @field_validator("letter")
    @classmethod
    def _letter_in_alphabet(cls, value: str) -> str:
        if value not in HEBREW_LETTERS:
            raise ValueError(f"letter must be one of constants.HEBREW_LETTERS, got {value!r}")
        return value

    @field_validator("glyph_form")
    @classmethod
    def _glyph_form_in_vocabulary(cls, value: str) -> str:
        if value not in GLYPH_FORMS:
            raise ValueError(f"glyph_form must be one of constants.GLYPH_FORMS, got {value!r}")
        return value

    @model_validator(mode="before")
    @classmethod
    def _default_glyph_form(cls, data: object) -> object:
        if isinstance(data, dict) and "glyph_form" not in data and "letter" in data:
            return {**data, "glyph_form": data["letter"]}
        return data

    @model_validator(mode="after")
    def _glyph_form_matches_base_letter(self) -> GlyphTarget:
        if BASE_LETTER_BY_GLYPH_FORM[self.glyph_form] != self.letter:
            raise ValueError("glyph_form must map to the same base letter as letter")
        return self
