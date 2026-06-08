"""ORM row for glyph_targets table."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from src.data.orm.base import Base


class GlyphTargetRow(Base):
    """Storage row for rendered Hebrew letter glyph contours — mirrors models.GlyphTarget."""

    __tablename__ = "glyph_targets"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    letter: Mapped[str]
    glyph_form: Mapped[str]
    font_name: Mapped[str]
    raster_size_px: Mapped[int]
    contour_path: Mapped[str]
    num_points: Mapped[int]
    num_contours: Mapped[int]
