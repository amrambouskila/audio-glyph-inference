"""ORM row for transform_candidates table."""
from __future__ import annotations

from src.data.orm.base import Base


class TransformCandidateRow(Base):
    """Storage row for a fitted candidate F_θ."""

    __tablename__ = "transform_candidates"
    # columns implemented in Phase 2