"""ORM row for transform_candidates table."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from src.data.orm.base import Base


class TransformCandidateRow(Base):
    """Storage row for a fitted candidate F_θ."""

    __tablename__ = "transform_candidates"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    # remaining columns implemented in Phase 2
