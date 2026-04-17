"""Tests for src/data/orm/experiment_run_row.py."""

from __future__ import annotations

from src.data.orm.base import Base
from src.data.orm.experiment_run_row import ExperimentRunRow


def test_experiment_run_row_inherits_declarative_base() -> None:
    assert issubclass(ExperimentRunRow, Base)


def test_experiment_run_row_tablename() -> None:
    assert ExperimentRunRow.__tablename__ == "experiment_runs"
