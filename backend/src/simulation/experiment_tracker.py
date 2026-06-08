"""Lightweight JSONL + Pydantic experiment tracker.

Phase 1: writes ExperimentRun and TransformCandidate records to
`experiments/runs/*.jsonl`. Phase 2+: optionally mirrored to MLflow
if we decide the tracker needs it (deferred; JSONL is the default).
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from src.models.experiment_run import ExperimentRun
from src.models.transform_candidate import TransformCandidate

_RUN_RECORD = "run"
_CANDIDATE_RECORD = "candidate"


class ExperimentTracker:
    """Standalone JSONL-backed experiment tracker."""

    def __init__(self, runs_dir: Path, *, create: bool = True) -> None:
        self.runs_dir = runs_dir
        if create:
            self.runs_dir.mkdir(parents=True, exist_ok=True)

    def log_run(self, run: ExperimentRun) -> None:
        self._append(run.id, _RUN_RECORD, run.model_dump(mode="json"))

    def log_candidate(
        self,
        run_id: str,
        candidate: TransformCandidate,
    ) -> None:
        self._append(UUID(run_id), _CANDIDATE_RECORD, candidate.model_dump(mode="json"))

    def read_run(self, run_id: str) -> tuple[ExperimentRun, list[TransformCandidate]]:
        """Replay one JSONL run ledger."""
        run: ExperimentRun | None = None
        candidates: list[TransformCandidate] = []
        path = self._run_path(UUID(run_id))
        if not path.exists():
            raise FileNotFoundError(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            kind = record["type"]
            payload = record["payload"]
            if kind == _RUN_RECORD:
                run = ExperimentRun(**payload)
            elif kind == _CANDIDATE_RECORD:
                candidates.append(TransformCandidate(**payload))
            else:
                raise ValueError(f"unknown experiment tracker record type {kind!r}")
        if run is None:
            raise ValueError(f"run ledger {path} does not contain a run record")
        return run, candidates

    def _append(self, run_id: UUID, record_type: str, payload: dict[str, object]) -> None:
        path = self._run_path(run_id)
        record = {"type": record_type, "payload": payload}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")

    def _run_path(self, run_id: UUID) -> Path:
        return self.runs_dir / f"{run_id}.jsonl"
