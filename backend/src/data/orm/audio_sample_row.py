"""ORM row for audio_samples table."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.data.orm.base import Base


class AudioSampleRow(Base):
    """Storage row for raw audio samples — mirrors models.AudioSample field-for-field.

    Uniqueness is (speaker_id, accent, letter, repetition); see master plan §3.2.
    """

    __tablename__ = "audio_samples"
    __table_args__ = (
        UniqueConstraint(
            "speaker_id",
            "accent",
            "letter",
            "pronunciation_variant",
            "repetition",
            name="uq_audio_sample_take",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    letter: Mapped[str]
    speaker_id: Mapped[str]
    accent: Mapped[str]
    repetition: Mapped[int]
    pronunciation_variant: Mapped[str]
    source: Mapped[str]
    file_path: Mapped[str]
    sample_rate_hz: Mapped[int]
    duration_s: Mapped[float]
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
