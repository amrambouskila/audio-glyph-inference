"""Tests for src/simulation/experiment_tracker.py."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from src.models.experiment_run import ExperimentRun
from src.models.transform_candidate import TransformCandidate
from src.simulation.experiment_tracker import ExperimentTracker


def _run() -> ExperimentRun:
    return ExperimentRun(
        id=uuid4(),
        name="phase-2-baseline",
        family="fourier_series",
        search_strategy="grid",
        dataset_split="train",
        scoring_metric="procrustes",
        regularization_weight=0.01,
        rng_seed=0,
        font_name="StamAshkenazCLM.ttf",
        config_snapshot={"audio_sample_rate_hz": 16_000},
        max_evaluations=1,
        started_at=datetime(2026, 4, 16, tzinfo=UTC),
    )


def _candidate() -> TransformCandidate:
    return TransformCandidate(
        id=uuid4(),
        family="fourier_series",
        theta={"rank_r": 1, "affine_b": [0.0, 1.0]},
        shared_across_letters=True,
        interpretability_score=0.5,
        simplicity_score=0.5,
        mean_shape_distance=1.0,
        lookup_ratio=0.0,
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )


def test_tracker_creates_runs_dir_and_replays_run(tmp_path) -> None:
    tracker = ExperimentTracker(tmp_path / "runs")
    run = _run()
    candidate = _candidate()

    tracker.log_run(run)
    tracker.log_candidate(str(run.id), candidate)
    rehydrated_run, candidates = tracker.read_run(str(run.id))

    assert rehydrated_run == run
    assert candidates == [candidate]
    ledger = tracker.runs_dir / f"{run.id}.jsonl"
    assert ledger.exists()
    lines = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert [line["type"] for line in lines] == ["run", "candidate"]


def test_tracker_can_open_missing_runs_dir_without_creating_it(tmp_path) -> None:
    runs_dir = tmp_path / "missing-runs"

    tracker = ExperimentTracker(runs_dir, create=False)

    assert tracker.runs_dir == runs_dir
    assert not runs_dir.exists()


def test_tracker_appends_multiple_candidates_in_order(tmp_path) -> None:
    tracker = ExperimentTracker(tmp_path)
    run = _run()
    first = _candidate()
    second = _candidate()

    tracker.log_run(run)
    tracker.log_candidate(str(run.id), first)
    tracker.log_candidate(str(run.id), second)
    _, candidates = tracker.read_run(str(run.id))

    assert candidates == [first, second]


def test_tracker_rejects_missing_unknown_and_runless_ledgers(tmp_path) -> None:
    tracker = ExperimentTracker(tmp_path)
    missing_id = uuid4()
    with pytest.raises(FileNotFoundError):
        tracker.read_run(str(missing_id))

    unknown_path = tmp_path / f"{missing_id}.jsonl"
    unknown_path.write_text(json.dumps({"type": "bad", "payload": {}}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown"):
        tracker.read_run(str(missing_id))

    runless_id = uuid4()
    candidate = _candidate()
    (tmp_path / f"{runless_id}.jsonl").write_text(
        json.dumps({"type": "candidate", "payload": candidate.model_dump(mode="json")}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not contain a run"):
        tracker.read_run(str(runless_id))
