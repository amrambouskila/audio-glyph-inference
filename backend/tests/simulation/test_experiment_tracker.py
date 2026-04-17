"""Tests for src/simulation/experiment_tracker.py (Phase 1 scaffold)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from src.models.experiment_run import ExperimentRun
from src.models.transform_candidate import TransformCandidate
from src.simulation.experiment_tracker import ExperimentTracker


def _run() -> ExperimentRun:
    return ExperimentRun(
        id=uuid4(),
        name="scaffold",
        family="fourier_series",
        search_strategy="grid",
        dataset_split="train",
        scoring_metric="procrustes",
        max_evaluations=1,
        started_at=datetime(2026, 4, 16, tzinfo=UTC),
    )


def _candidate() -> TransformCandidate:
    return TransformCandidate(
        id=uuid4(),
        family="fourier_series",
        theta={"a0": 0.0},
        shared_across_letters=True,
        interpretability_score=0.5,
        simplicity_score=0.5,
        mean_shape_distance=1.0,
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )


def test_constructor_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        ExperimentTracker(runs_dir=Path("/tmp/scaffold"))


def test_log_run_is_scaffold_stub() -> None:
    tracker = ExperimentTracker.__new__(ExperimentTracker)
    with pytest.raises(NotImplementedError):
        tracker.log_run(_run())


def test_log_candidate_is_scaffold_stub() -> None:
    tracker = ExperimentTracker.__new__(ExperimentTracker)
    with pytest.raises(NotImplementedError):
        tracker.log_candidate(run_id="run-1", candidate=_candidate())
