"""Tests for scripts/seed_live_smoke.py."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scripts.seed_live_smoke import main, seed_live_smoke_data
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from src.config import BackendSettings
from src.constants import NUM_GLYPH_FORMS
from src.data.orm.experiment_run_row import ExperimentRunRow
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.transform_candidate_row import TransformCandidateRow
from src.simulation.contour_io import load_contours
from src.simulation.experiment_tracker import ExperimentTracker
from src.simulation.transforms.lissajous import LissajousFamily
from tests.conftest import FONT_PATH


def _settings(postgres_url: str, tmp_path: Path) -> BackendSettings:
    return BackendSettings(
        database_url=postgres_url,
        font_file=FONT_PATH,
        contours_dir=tmp_path / "contours",
        experiments_dir=tmp_path / "experiments",
    )


async def test_seed_live_smoke_data_creates_catalog_visible_rows(
    db_session: AsyncSession,
    postgres_url: str,
    tmp_path: Path,
) -> None:
    settings = _settings(postgres_url, tmp_path)
    glyphs, run, candidate = await seed_live_smoke_data(
        db_session,
        settings,
        ExperimentTracker(settings.experiments_dir),
    )

    assert len(glyphs) == NUM_GLYPH_FORMS
    assert run.name == "live-smoke-seed"
    assert run.completed_at is not None
    assert run.best_candidate_id == candidate.id
    assert candidate.family == "lissajous"
    assert candidate.mean_shape_distance == 1.0
    assert candidate.lookup_ratio == 1.0

    glyph_count = await db_session.scalar(select(func.count()).select_from(GlyphTargetRow))
    run_count = await db_session.scalar(select(func.count()).select_from(ExperimentRunRow))
    candidate_count = await db_session.scalar(select(func.count()).select_from(TransformCandidateRow))
    assert glyph_count == NUM_GLYPH_FORMS
    assert run_count == 1
    assert candidate_count == 1

    contours = load_contours(Path(glyphs[0].contour_path))
    assert contours
    assert all(contour.shape[1] == 2 for contour in contours)

    generated = LissajousFamily().forward(_smoke_audio(settings), candidate.theta)
    assert generated.shape == (settings.glyph_contour_num_points, 2)
    assert generated.dtype == np.float64

    tracked_run, tracked_candidates = ExperimentTracker(settings.experiments_dir).read_run(str(run.id))
    assert tracked_run.id == run.id
    assert [tracked.id for tracked in tracked_candidates] == [candidate.id]


async def test_seed_live_smoke_data_reuses_existing_glyphs(
    db_session: AsyncSession,
    postgres_url: str,
    tmp_path: Path,
) -> None:
    settings = _settings(postgres_url, tmp_path)
    tracker = ExperimentTracker(settings.experiments_dir)

    first_glyphs, _, _ = await seed_live_smoke_data(db_session, settings, tracker)
    second_glyphs, _, _ = await seed_live_smoke_data(db_session, settings, tracker)

    glyph_count = await db_session.scalar(select(func.count()).select_from(GlyphTargetRow))
    run_count = await db_session.scalar(select(func.count()).select_from(ExperimentRunRow))
    candidate_count = await db_session.scalar(select(func.count()).select_from(TransformCandidateRow))
    assert glyph_count == NUM_GLYPH_FORMS
    assert run_count == 2
    assert candidate_count == 2
    assert {glyph.id for glyph in first_glyphs} == {glyph.id for glyph in second_glyphs}


def test_main_seeds_with_cli_overrides(
    postgres_url: str,
    db_engine: AsyncEngine,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert db_engine is not None

    result = main(
        [
            "--database-url",
            postgres_url,
            "--font-file",
            str(FONT_PATH),
            "--contours-dir",
            str(tmp_path / "contours"),
            "--experiments-dir",
            str(tmp_path / "experiments"),
        ]
    )

    assert result == 0
    assert "Seeded live smoke data: 27 glyph targets" in capsys.readouterr().out


def _smoke_audio(settings: BackendSettings) -> np.ndarray:
    phase = np.linspace(0.0, 2.0 * np.pi, settings.audio_frame_length_samples, endpoint=False)
    frame = np.sin(phase)
    return np.tile(frame, (settings.feature_n_segments, 1)).astype(np.float64)
