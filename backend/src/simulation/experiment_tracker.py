"""Lightweight JSONL + Pydantic experiment tracker.

Phase 1: writes ExperimentRun and TransformCandidate records to
`experiments/runs/*.jsonl`. Phase 2+: optionally mirrored to MLflow
if we decide the tracker needs it (deferred; JSONL is the default).
"""
from __future__ import annotations

from pathlib import Path

from src.models.experiment_run import ExperimentRun
from src.models.transform_candidate import TransformCandidate


class ExperimentTracker:
    """Standalone JSONL-backed experiment tracker."""

    def __init__(self, runs_dir: Path) -> None:
        raise NotImplementedError

    def log_run(self, run: ExperimentRun) -> None:
        raise NotImplementedError

    def log_candidate(
        self,
        run_id: str,
        candidate: TransformCandidate,
    ) -> None:
        raise NotImplementedError