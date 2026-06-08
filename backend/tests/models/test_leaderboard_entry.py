"""Tests for src/models/leaderboard_entry.py."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from src.models.leaderboard_entry import LeaderboardEntry


def test_leaderboard_entry_round_trips_rank_fields() -> None:
    entry = LeaderboardEntry(
        family="fourier_series",
        run_id=uuid4(),
        run_name="baseline",
        candidate_id=uuid4(),
        search_strategy="grid",
        scoring_metric="procrustes",
        held_out_accent="chabad",
        shared_across_letters=True,
        mean_shape_distance=0.1,
        simplicity_score=0.8,
        interpretability_score=0.7,
        lookup_ratio=0.2,
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )
    dumped = entry.model_dump()
    assert dumped["family"] == "fourier_series"
    assert dumped["held_out_accent"] == "chabad"
    assert dumped["shared_across_letters"] is True
