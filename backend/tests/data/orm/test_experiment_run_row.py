"""Tests for src/data/orm/experiment_run_row.py."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from src.data.orm.base import Base
from src.data.orm.experiment_run_row import ExperimentRunRow
from src.models.experiment_run import ExperimentRun


def _row(**overrides) -> ExperimentRunRow:
    fields = {
        "id": uuid4(),
        "name": "phase-2-baseline",
        "family": "fourier_series",
        "search_strategy": "grid",
        "dataset_split": "train",
        "scoring_metric": "procrustes",
        "regularization_weight": 0.01,
        "held_out_accent": "ashkenazi",
        "rng_seed": 9,
        "font_name": "StamAshkenazCLM.ttf",
        "config_snapshot": {"audio_sample_rate_hz": 16_000, "enabled": True},
        "max_evaluations": 12,
        "started_at": datetime(2026, 4, 16, tzinfo=UTC),
        "completed_at": None,
        "best_candidate_id": None,
    }
    fields.update(overrides)
    return ExperimentRunRow(**fields)


def test_experiment_run_row_inherits_declarative_base() -> None:
    assert issubclass(ExperimentRunRow, Base)


def test_experiment_run_row_tablename() -> None:
    assert ExperimentRunRow.__tablename__ == "experiment_runs"


def test_experiment_run_row_columns_match_model_contract() -> None:
    assert set(ExperimentRunRow.__table__.columns.keys()) == {
        "id",
        "name",
        "family",
        "search_strategy",
        "dataset_split",
        "scoring_metric",
        "regularization_weight",
        "held_out_accent",
        "rng_seed",
        "font_name",
        "config_snapshot",
        "max_evaluations",
        "started_at",
        "completed_at",
        "best_candidate_id",
    }


async def test_experiment_run_row_round_trips(db_session) -> None:
    candidate_id = uuid4()
    row = _row(completed_at=datetime(2026, 4, 17, tzinfo=UTC), best_candidate_id=candidate_id)
    db_session.add(row)
    await db_session.commit()

    fetched = (await db_session.execute(select(ExperimentRunRow).where(ExperimentRunRow.id == row.id))).scalar_one()
    model = ExperimentRun.model_validate(fetched)

    assert model.family == "fourier_series"
    assert model.config_snapshot["enabled"] is True
    assert model.completed_at is not None
    assert model.best_candidate_id == candidate_id
