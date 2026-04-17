"""AudioSample — one recording of a single Hebrew letter being spoken.

A sample is raw; preprocessing (resampling, loudness-norm, framing)
happens at the boundary into `simulation/audio_preprocessor.py`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AudioSample(BaseModel):
    """Single raw audio sample of a spoken Hebrew letter."""

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
    source: str = Field(
        description="Origin of the recording ('user' is the default in Phase 1).",
    )
    file_path: str = Field(
        description="Absolute path to the raw audio file inside the container.",
    )
    sample_rate_hz: int
    duration_s: float
    recorded_at: datetime
