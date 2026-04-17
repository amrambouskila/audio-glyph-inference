"""ORM row for glyph_targets table."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from src.data.orm.base import Base


class GlyphTargetRow(Base):
    """Storage row for rendered Hebrew letter glyph contours."""

    __tablename__ = "glyph_targets"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    # remaining columns implemented in Phase 1
