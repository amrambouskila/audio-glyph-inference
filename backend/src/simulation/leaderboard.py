"""Per-family leaderboard replay from JSONL experiment ledgers."""

from __future__ import annotations

from src.models.leaderboard_entry import LeaderboardEntry
from src.simulation.experiment_tracker import ExperimentTracker


def build_family_leaderboards(
    tracker: ExperimentTracker,
    *,
    shared_only: bool = True,
    family: str | None = None,
    limit: int | None = None,
) -> dict[str, list[LeaderboardEntry]]:
    """Replay experiment ledgers into sorted per-family leaderboards."""
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive or None")
    entries: dict[str, list[LeaderboardEntry]] = {}
    for path in sorted(tracker.runs_dir.glob("*.jsonl")):
        run, candidates = tracker.read_run(path.stem)
        for candidate in candidates:
            if shared_only and not candidate.shared_across_letters:
                continue
            if family is not None and candidate.family != family:
                continue
            entries.setdefault(candidate.family, []).append(
                LeaderboardEntry(
                    family=candidate.family,
                    run_id=run.id,
                    run_name=run.name,
                    candidate_id=candidate.id,
                    search_strategy=run.search_strategy,
                    scoring_metric=run.scoring_metric,
                    held_out_accent=run.held_out_accent,
                    shared_across_letters=candidate.shared_across_letters,
                    mean_shape_distance=candidate.mean_shape_distance,
                    simplicity_score=candidate.simplicity_score,
                    interpretability_score=candidate.interpretability_score,
                    lookup_ratio=candidate.lookup_ratio,
                    created_at=candidate.created_at,
                )
            )
    return {
        family_name: _limit(_sort_entries(family_entries), limit)
        for family_name, family_entries in sorted(entries.items())
    }


def _sort_entries(entries: list[LeaderboardEntry]) -> list[LeaderboardEntry]:
    return sorted(
        entries,
        key=lambda entry: (
            entry.mean_shape_distance,
            entry.lookup_ratio,
            -entry.simplicity_score,
            -entry.interpretability_score,
            entry.created_at,
            str(entry.candidate_id),
        ),
    )


def _limit(entries: list[LeaderboardEntry], limit: int | None) -> list[LeaderboardEntry]:
    if limit is None:
        return entries
    return entries[:limit]
