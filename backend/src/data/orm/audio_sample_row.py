"""ORM row for audio_samples table."""

from __future__ import annotations

from src.data.orm.base import Base


class AudioSampleRow(Base):
    """Storage row for raw audio samples.

    Must mirror src/models/audio_sample.AudioSample field-for-field —
    including the `accent` column (one of constants.ACCENTS). See
    docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md §11.1 + §11.3 for why.
    """

    __tablename__ = "audio_samples"
    # columns implemented in Phase 1
