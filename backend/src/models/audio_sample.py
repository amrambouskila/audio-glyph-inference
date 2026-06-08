"""AudioSample — one recording of a single Hebrew letter being spoken.

A sample is raw; preprocessing (resampling, loudness-norm, framing)
happens at the boundary into `simulation/audio_preprocessor.py`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.constants import ACCENTS, HEBREW_LETTERS, PRONUNCIATION_VARIANTS_BY_BASE_LETTER

PronunciationVariant = Literal["plain", "hard", "soft"]


class AudioSample(BaseModel):
    """Single raw audio sample of a spoken Hebrew letter.

    Storage uniqueness is (speaker_id, accent, letter, repetition) — see
    docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md §3.2; the ORM row enforces it.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    letter: str = Field(
        description="One of the 22 Hebrew letters in constants.HEBREW_LETTERS.",
    )
    speaker_id: str = Field(
        description="Opaque speaker identifier. In Phase 1 all samples come from the project owner.",
    )
    accent: str = Field(
        description=(
            "Pronunciation tradition: one of constants.ACCENTS "
            "('ashkenazi' | 'sephardi' | 'moroccan' | 'yemenite' | 'chabad'). "
            "Primary axis for generalization splits — see master plan §11.3."
        ),
    )
    repetition: int = Field(
        gt=0,
        description="1-based repetition index within a (speaker_id, accent, letter) recording block.",
    )
    pronunciation_variant: PronunciationVariant = Field(
        default="plain",
        description="Pronunciation variant for the base letter: plain, hard, or soft.",
    )
    source: str = Field(
        description="Origin of the recording ('user' is the default in Phase 1).",
    )
    file_path: str = Field(
        description="Absolute path to the raw audio file inside the container.",
    )
    sample_rate_hz: int
    duration_s: float
    recorded_at: datetime

    @field_validator("letter")
    @classmethod
    def _letter_in_alphabet(cls, value: str) -> str:
        if value not in HEBREW_LETTERS:
            raise ValueError(f"letter must be one of constants.HEBREW_LETTERS, got {value!r}")
        return value

    @field_validator("accent")
    @classmethod
    def _accent_in_vocabulary(cls, value: str) -> str:
        if value not in ACCENTS:
            raise ValueError(f"accent must be one of constants.ACCENTS, got {value!r}")
        return value

    @model_validator(mode="after")
    def _variant_allowed_for_letter(self) -> AudioSample:
        allowed = PRONUNCIATION_VARIANTS_BY_BASE_LETTER[self.letter]
        if self.pronunciation_variant not in allowed:
            raise ValueError(f"pronunciation_variant must be one of {allowed!r} for letter {self.letter!r}")
        return self
