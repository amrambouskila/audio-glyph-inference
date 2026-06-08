"""PairedExample — a single (audio, target glyph) training tuple.

This is the atomic unit of the dataset. All transform-family search runs
iterate over PairedExample instances, not raw AudioSample / GlyphTarget.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from src.constants import (
    BASE_LETTER_BY_GLYPH_FORM,
    GLYPH_FORMS,
    HEBREW_LETTERS,
    PRONUNCIATION_VARIANTS_BY_BASE_LETTER,
)

PronunciationVariant = Literal["plain", "hard", "soft"]


class PairedExample(BaseModel):
    """One training pair: spoken letter audio bound to its target glyph.

    `split` is assigned per accent (leave-one-accent-out); see master plan §11.3.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    audio_sample_id: UUID
    glyph_target_id: UUID
    letter: str
    pronunciation_variant: PronunciationVariant = "plain"
    glyph_form: str
    split: Literal["train", "val", "test"]

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
    def _forms_match_base_letter(self) -> PairedExample:
        if self.pronunciation_variant not in PRONUNCIATION_VARIANTS_BY_BASE_LETTER[self.letter]:
            raise ValueError("pronunciation_variant is not valid for letter")
        if BASE_LETTER_BY_GLYPH_FORM[self.glyph_form] != self.letter:
            raise ValueError("glyph_form must map to the same base letter as letter")
        return self
