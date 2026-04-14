"""ORM row for experiment_runs table."""
from __future__ import annotations

from src.data.orm.base import Base


class ExperimentRunRow(Base):
    """Storage row for a configured transform-family search run."""

    __tablename__ = "experiment_runs"
    # columns implemented in Phase 2