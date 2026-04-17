"""ORM row for paired_examples table."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from src.data.orm.base import Base


class PairedExampleRow(Base):
    """Storage row binding an audio sample to a target glyph."""

    __tablename__ = "paired_examples"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    # remaining columns implemented in Phase 1
