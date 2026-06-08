"""ORM row for experiment_runs table."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.data.orm.base import Base


class ExperimentRunRow(Base):
    """Storage row for a configured transform-family search run."""

    __tablename__ = "experiment_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str]
    family: Mapped[str]
    search_strategy: Mapped[str]
    dataset_split: Mapped[str]
    scoring_metric: Mapped[str]
    regularization_weight: Mapped[float]
    held_out_accent: Mapped[str | None]
    rng_seed: Mapped[int]
    font_name: Mapped[str]
    config_snapshot: Mapped[dict[str, str | int | float | bool]] = mapped_column(JSONB)
    max_evaluations: Mapped[int]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    best_candidate_id: Mapped[UUID | None]
