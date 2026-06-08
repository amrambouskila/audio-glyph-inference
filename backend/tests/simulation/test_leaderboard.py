"""Tests for src/simulation/leaderboard.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import numpy as np
import pytest
from src.models.experiment_run import ExperimentRun
from src.models.transform_candidate import TransformCandidate
from src.simulation.experiment_tracker import ExperimentTracker
from src.simulation.leaderboard import _limit, _sort_entries, build_family_leaderboards


def _run(family: str, name: str) -> ExperimentRun:
    return ExperimentRun(
        id=uuid4(),
        name=name,
        family=family,
        search_strategy="grid",
        dataset_split="train",
        scoring_metric="procrustes",
        regularization_weight=0.0,
        held_out_accent="chabad",
        rng_seed=7,
        font_name="StamAshkenazCLM.ttf",
        config_snapshot={"search_grid_resolution": 5},
        max_evaluations=5,
        started_at=datetime(2026, 4, 16, tzinfo=UTC),
        completed_at=datetime(2026, 4, 16, 0, 1, tzinfo=UTC),
    )


def _candidate(
    family: str,
    distance: float,
    *,
    shared: bool = True,
    lookup_ratio: float = 0.5,
    simplicity: float = 0.5,
    interpretability: float = 0.5,
    seconds: int = 0,
) -> TransformCandidate:
    return TransformCandidate(
        id=uuid4(),
        family=family,
        theta={"rank_r": 1},
        shared_across_letters=shared,
        interpretability_score=interpretability,
        simplicity_score=simplicity,
        mean_shape_distance=distance,
        lookup_ratio=lookup_ratio,
        created_at=datetime(2026, 4, 16, tzinfo=UTC) + timedelta(seconds=seconds),
    )


def test_build_family_leaderboards_groups_sorts_and_filters_shared_candidates(tmp_path) -> None:
    tracker = ExperimentTracker(tmp_path)
    fourier_run = _run("fourier_series", "fourier")
    lissajous_run = _run("lissajous", "lissajous")
    worse = _candidate("fourier_series", 0.3, seconds=2)
    best = _candidate("fourier_series", 0.1, seconds=1)
    lookup_reference = _candidate("fourier_series", 0.0, shared=False)
    other_family = _candidate("lissajous", 0.2)

    tracker.log_run(fourier_run)
    tracker.log_candidate(str(fourier_run.id), worse)
    tracker.log_candidate(str(fourier_run.id), best)
    tracker.log_candidate(str(fourier_run.id), lookup_reference)
    tracker.log_run(lissajous_run)
    tracker.log_candidate(str(lissajous_run.id), other_family)

    leaderboards = build_family_leaderboards(tracker)

    assert set(leaderboards) == {"fourier_series", "lissajous"}
    assert [entry.candidate_id for entry in leaderboards["fourier_series"]] == [best.id, worse.id]
    assert leaderboards["fourier_series"][0].run_name == "fourier"
    np.testing.assert_allclose(leaderboards["lissajous"][0].mean_shape_distance, 0.2, atol=1e-12)


def test_build_family_leaderboards_can_include_per_letter_references_filter_family_and_limit(tmp_path) -> None:
    tracker = ExperimentTracker(tmp_path)
    run = _run("fourier_series", "with-reference")
    shared = _candidate("fourier_series", 0.3, shared=True)
    reference = _candidate("fourier_series", 0.1, shared=False)
    tracker.log_run(run)
    tracker.log_candidate(str(run.id), shared)
    tracker.log_candidate(str(run.id), reference)

    leaderboards = build_family_leaderboards(tracker, shared_only=False, family="fourier_series", limit=1)

    assert set(leaderboards) == {"fourier_series"}
    assert leaderboards["fourier_series"][0].candidate_id == reference.id
    assert leaderboards["fourier_series"][0].shared_across_letters is False


def test_build_family_leaderboards_returns_empty_for_no_matches(tmp_path) -> None:
    tracker = ExperimentTracker(tmp_path)
    assert build_family_leaderboards(tracker) == {}
    run = _run("fourier_series", "baseline")
    tracker.log_run(run)
    tracker.log_candidate(str(run.id), _candidate("fourier_series", 0.1))
    assert build_family_leaderboards(tracker, family="lissajous") == {}


def test_build_family_leaderboards_validates_limit(tmp_path) -> None:
    with pytest.raises(ValueError, match="limit"):
        build_family_leaderboards(ExperimentTracker(tmp_path), limit=0)


def test_sort_entries_tie_breaks_on_lookup_and_scores(tmp_path) -> None:
    tracker = ExperimentTracker(tmp_path)
    run = _run("fourier_series", "ties")
    low_lookup = _candidate("fourier_series", 0.2, lookup_ratio=0.1, simplicity=0.1, interpretability=0.1)
    high_simplicity = _candidate("fourier_series", 0.2, lookup_ratio=0.2, simplicity=0.9, interpretability=0.1)
    high_interpretability = _candidate("fourier_series", 0.2, lookup_ratio=0.2, simplicity=0.8, interpretability=0.9)
    tracker.log_run(run)
    for candidate in [high_interpretability, high_simplicity, low_lookup]:
        tracker.log_candidate(str(run.id), candidate)

    entries = build_family_leaderboards(tracker)["fourier_series"]

    assert [entry.candidate_id for entry in entries] == [low_lookup.id, high_simplicity.id, high_interpretability.id]
    assert _limit(_sort_entries(entries), 2) == entries[:2]
