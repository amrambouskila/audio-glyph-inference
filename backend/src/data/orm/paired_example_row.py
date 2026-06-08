"""ORM row for paired_examples table."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.data.orm.base import Base


class PairedExampleRow(Base):
    """Storage row binding an audio sample to a target glyph — mirrors models.PairedExample."""

    __tablename__ = "paired_examples"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    audio_sample_id: Mapped[UUID] = mapped_column(ForeignKey("audio_samples.id"))
    glyph_target_id: Mapped[UUID] = mapped_column(ForeignKey("glyph_targets.id"))
    letter: Mapped[str]
    pronunciation_variant: Mapped[str]
    glyph_form: Mapped[str]
    split: Mapped[str]
