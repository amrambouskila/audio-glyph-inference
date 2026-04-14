"""ORM row for glyph_targets table."""
from __future__ import annotations

from src.data.orm.base import Base


class GlyphTargetRow(Base):
    """Storage row for rendered Hebrew letter glyph contours."""

    __tablename__ = "glyph_targets"
    # columns implemented in Phase 1