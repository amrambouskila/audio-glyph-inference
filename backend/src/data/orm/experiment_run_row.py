"""ORM row for experiment_runs table."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from src.data.orm.base import Base


class ExperimentRunRow(Base):
    """Storage row for a configured transform-family search run."""

    __tablename__ = "experiment_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    # remaining columns implemented in Phase 2
