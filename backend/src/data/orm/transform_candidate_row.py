"""ORM row for transform_candidates table."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.data.orm.base import Base
from src.models.transform_candidate import ThetaValue


class TransformCandidateRow(Base):
    """Storage row for a fitted candidate F_theta."""

    __tablename__ = "transform_candidates"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    family: Mapped[str]
    theta: Mapped[dict[str, ThetaValue]] = mapped_column(JSONB)
    expression: Mapped[str | None]
    shared_across_letters: Mapped[bool]
    interpretability_score: Mapped[float]
    simplicity_score: Mapped[float]
    mean_shape_distance: Mapped[float]
    lookup_ratio: Mapped[float]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
