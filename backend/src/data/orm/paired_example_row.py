"""ORM row for paired_examples table."""

from __future__ import annotations

from src.data.orm.base import Base


class PairedExampleRow(Base):
    """Storage row binding an audio sample to a target glyph."""

    __tablename__ = "paired_examples"
    # columns implemented in Phase 1
