"""Tests for src/models/experiment_run.py."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.models.experiment_run import ExperimentRun


def _valid_payload() -> dict:
    return {
        "id": uuid4(),
        "name": "phase-2-baseline",
        "family": "fourier_series",
        "search_strategy": "cma-es",
        "dataset_split": "train",
        "scoring_metric": "procrustes",
        "max_evaluations": 1000,
        "started_at": datetime(2026, 4, 16, tzinfo=UTC),
    }


def test_round_trip_with_optional_fields_none() -> None:
    run = ExperimentRun(**_valid_payload())
    assert run.completed_at is None
    assert run.best_candidate_id is None
    rehydrated = ExperimentRun(**run.model_dump())
    assert rehydrated == run


def test_round_trip_with_optional_fields_populated() -> None:
    payload = _valid_payload()
    payload["completed_at"] = datetime(2026, 4, 17, tzinfo=UTC)
    payload["best_candidate_id"] = uuid4()
    run = ExperimentRun(**payload)
    assert run.completed_at is not None
    assert run.best_candidate_id is not None


def test_missing_required_field_raises() -> None:
    payload = _valid_payload()
    del payload["search_strategy"]
    with pytest.raises(ValidationError):
        ExperimentRun(**payload)
