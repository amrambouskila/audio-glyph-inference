"""Transform-search experiment runs."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import anyio
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_experiment_tracker, get_session, get_settings_dep
from src.config import BackendSettings
from src.config_snapshot import config_snapshot
from src.data.orm.audio_sample_row import AudioSampleRow
from src.data.orm.experiment_run_row import ExperimentRunRow
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.paired_example_row import PairedExampleRow
from src.data.orm.transform_candidate_row import TransformCandidateRow
from src.models.experiment_create import ExperimentCreate
from src.models.experiment_detail import ExperimentDetail
from src.models.experiment_run import ExperimentRun
from src.models.transform_candidate import TransformCandidate
from src.simulation.audio_preprocessor import AudioPreprocessor
from src.simulation.contour_io import load_contours
from src.simulation.experiment_tracker import ExperimentTracker
from src.simulation.search_engine import SearchEngine
from src.simulation.symbolic_search import PySRUnavailableError, require_symbolic_regressor_factory
from src.simulation.transforms.family_registry import build_family

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentDetail, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    body: ExperimentCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[BackendSettings, Depends(get_settings_dep)],
    tracker: Annotated[ExperimentTracker, Depends(get_experiment_tracker)],
) -> ExperimentDetail:
    try:
        family = build_family(body.family, settings)
        if body.search_strategy == "symbolic-regression":
            require_symbolic_regressor_factory()
        engine = SearchEngine(
            family=family,
            distance_metric=body.scoring_metric,
            strategy=body.search_strategy,
            max_evaluations=body.max_evaluations,
            regularization_weight=body.regularization_weight,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except PySRUnavailableError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    samples = await _load_dataset(session, body.dataset_split, body.held_out_accent)
    if not samples:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "no paired examples match the experiment slice")

    run = ExperimentRun(
        id=uuid4(),
        name=body.name,
        family=body.family,
        search_strategy=body.search_strategy,
        dataset_split=body.dataset_split,
        scoring_metric=body.scoring_metric,
        regularization_weight=body.regularization_weight,
        held_out_accent=body.held_out_accent,
        rng_seed=body.rng_seed,
        font_name=settings.font_file.name,
        config_snapshot=config_snapshot(settings),
        max_evaluations=body.max_evaluations,
        started_at=datetime.now(tz=UTC),
    )
    run_row = ExperimentRunRow(**run.model_dump())
    session.add(run_row)
    await session.commit()
    tracker.log_run(run)

    audio, targets, letters, accents = await anyio.to_thread.run_sync(_materialize_samples, samples, settings)
    try:
        candidates = await anyio.to_thread.run_sync(
            partial(
                engine.fit,
                audio,
                targets,
                letters,
                accents,
                shared_across_letters=body.shared_across_letters,
                seed=body.rng_seed,
            )
        )
    except PySRUnavailableError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    for candidate in candidates:
        session.add(TransformCandidateRow(**candidate.model_dump()))
        tracker.log_candidate(str(run.id), candidate)
    best = candidates[0] if candidates else None
    run.completed_at = datetime.now(tz=UTC)
    run.best_candidate_id = best.id if best is not None else None
    run_row.completed_at = run.completed_at
    run_row.best_candidate_id = run.best_candidate_id
    await session.commit()
    tracker.log_run(run)
    return ExperimentDetail(run=run, best_candidate=best, candidate_count=len(candidates))


@router.get("", response_model=list[ExperimentRun])
async def list_experiments(
    session: Annotated[AsyncSession, Depends(get_session)],
    family: Annotated[str | None, Query()] = None,
    strategy: Annotated[str | None, Query()] = None,
    held_out_accent: Annotated[str | None, Query()] = None,
    run_status: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ExperimentRun]:
    stmt = select(ExperimentRunRow)
    if family is not None:
        stmt = stmt.where(ExperimentRunRow.family == family)
    if strategy is not None:
        stmt = stmt.where(ExperimentRunRow.search_strategy == strategy)
    if held_out_accent is not None:
        stmt = stmt.where(ExperimentRunRow.held_out_accent == held_out_accent)
    stmt = stmt.order_by(ExperimentRunRow.started_at.desc()).limit(limit).offset(offset)
    rows = (await session.execute(stmt)).scalars().all()
    runs = [ExperimentRun.model_validate(row) for row in rows]
    if run_status is not None:
        runs = [run for run in runs if _derived_status(run) == run_status]
    return runs


@router.get("/{run_id}", response_model=ExperimentDetail)
async def get_experiment(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    tracker: Annotated[ExperimentTracker, Depends(get_experiment_tracker)],
) -> ExperimentDetail:
    try:
        parsed_run_id = UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "experiment run not found") from exc
    row = await session.get(ExperimentRunRow, parsed_run_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "experiment run not found")
    run = ExperimentRun.model_validate(row)
    best = None
    if run.best_candidate_id is not None:
        candidate_row = await session.get(TransformCandidateRow, run.best_candidate_id)
        best = TransformCandidate.model_validate(candidate_row) if candidate_row is not None else None
    try:
        _, candidates = tracker.read_run(str(run.id))
    except FileNotFoundError:
        candidates = []
    return ExperimentDetail(run=run, best_candidate=best, candidate_count=len(candidates))


def _derived_status(run: ExperimentRun) -> str:
    return "completed" if run.completed_at is not None else "running"


async def _load_dataset(
    session: AsyncSession,
    dataset_split: str,
    held_out_accent: str | None,
) -> list[tuple[AudioSampleRow, GlyphTargetRow]]:
    stmt = (
        select(AudioSampleRow, GlyphTargetRow)
        .join(PairedExampleRow, PairedExampleRow.audio_sample_id == AudioSampleRow.id)
        .join(GlyphTargetRow, GlyphTargetRow.id == PairedExampleRow.glyph_target_id)
        .where(PairedExampleRow.split == dataset_split)
    )
    if held_out_accent is not None:
        stmt = stmt.where(AudioSampleRow.accent != held_out_accent)
    result = await session.execute(stmt)
    return [(audio, glyph) for audio, glyph in result.all()]


def _materialize_samples(
    rows: list[tuple[AudioSampleRow, GlyphTargetRow]],
    settings: BackendSettings,
) -> tuple[list[np.ndarray], np.ndarray, list[str], list[str]]:
    preprocessor = AudioPreprocessor(
        target_sample_rate_hz=settings.audio_sample_rate_hz,
        frame_length_samples=settings.audio_frame_length_samples,
        hop_length_samples=settings.audio_hop_length_samples,
        duration_min_s=settings.audio_duration_min_s,
        duration_max_s=settings.audio_duration_max_s,
        active_speech_min_s=settings.audio_active_speech_min_s,
        active_speech_max_s=settings.audio_active_speech_max_s,
        peak_dbfs_max=settings.audio_peak_dbfs_max,
        target_lufs=settings.audio_target_lufs,
        vad_top_db=settings.audio_vad_top_db,
    )
    audio = [preprocessor.load(Path(audio_row.file_path)).frames for audio_row, _ in rows]
    targets = np.stack([np.vstack(load_contours(Path(glyph_row.contour_path))) for _, glyph_row in rows]).astype(
        np.float64
    )
    letters = [audio_row.letter for audio_row, _ in rows]
    accents = [audio_row.accent for audio_row, _ in rows]
    return audio, targets, letters, accents
