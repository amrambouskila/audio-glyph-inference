"""Seed deterministic non-empirical rows for Phase-4 live-loop smoke testing."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import BackendSettings, get_settings
from src.config_snapshot import config_snapshot
from src.constants import BASE_LETTER_BY_GLYPH_FORM, GLYPH_FORMS
from src.data.database import create_engine, session_scope
from src.data.orm.experiment_run_row import ExperimentRunRow
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.transform_candidate_row import TransformCandidateRow
from src.models.experiment_run import ExperimentRun
from src.models.glyph_target import GlyphTarget
from src.models.transform_candidate import TransformCandidate
from src.simulation.contour_io import save_contours
from src.simulation.experiment_tracker import ExperimentTracker
from src.simulation.glyph_extractor import GlyphExtractor
from src.simulation.scoring import interpretability_score, simplicity_score
from src.simulation.transforms.lissajous import LissajousFamily
from src.simulation.transforms.transform_base import Theta

_SMOKE_RUN_NAME = "live-smoke-seed"
_SMOKE_DATASET_SPLIT = "smoke"
_SMOKE_MAX_EVALUATIONS = 1
_SMOKE_RNG_SEED = 0
_SMOKE_MEAN_DISTANCE = 1.0
_SMOKE_LOOKUP_RATIO = 1.0


async def seed_live_smoke_data(
    session: AsyncSession,
    settings: BackendSettings,
    tracker: ExperimentTracker,
) -> tuple[list[GlyphTarget], ExperimentRun, TransformCandidate]:
    """Create glyph targets plus one catalog-visible smoke candidate/run."""
    glyphs = await _seed_glyphs(session, settings)
    candidate = _smoke_candidate(settings)
    run = ExperimentRun(
        id=uuid4(),
        name=_SMOKE_RUN_NAME,
        family=candidate.family,
        search_strategy="grid",
        dataset_split=_SMOKE_DATASET_SPLIT,
        scoring_metric="chamfer",
        regularization_weight=settings.search_default_lambda,
        held_out_accent=None,
        rng_seed=_SMOKE_RNG_SEED,
        font_name=settings.font_file.name,
        config_snapshot=config_snapshot(settings),
        max_evaluations=_SMOKE_MAX_EVALUATIONS,
        started_at=datetime.now(tz=UTC),
        completed_at=datetime.now(tz=UTC),
        best_candidate_id=candidate.id,
    )
    session.add(TransformCandidateRow(**candidate.model_dump()))
    session.add(ExperimentRunRow(**run.model_dump()))
    await session.commit()
    tracker.log_run(run)
    tracker.log_candidate(str(run.id), candidate)
    return glyphs, run, candidate


def main(argv: Sequence[str] | None = None) -> int:
    """Run the live smoke-data seeder."""
    parser = argparse.ArgumentParser(
        description="Seed glyph targets and a non-empirical live smoke candidate for the Phase-4 browser UI.",
    )
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--font-file", type=Path, default=None)
    parser.add_argument("--contours-dir", type=Path, default=None)
    parser.add_argument("--experiments-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    settings = get_settings()
    overrides: dict[str, object] = {}
    if args.database_url is not None:
        overrides["database_url"] = args.database_url
    if args.font_file is not None:
        overrides["font_file"] = args.font_file
    if args.contours_dir is not None:
        overrides["contours_dir"] = args.contours_dir
    if args.experiments_dir is not None:
        overrides["experiments_dir"] = args.experiments_dir
    if overrides:
        values = settings.model_dump()
        values.update(overrides)
        settings = BackendSettings(**values)

    result = asyncio.run(_seed_with_own_session(settings))
    print(f"Seeded live smoke data: {len(result[0])} glyph targets, run_id={result[1].id}, candidate_id={result[2].id}")
    return 0


async def _seed_glyphs(session: AsyncSession, settings: BackendSettings) -> list[GlyphTarget]:
    extractor = GlyphExtractor(
        font_path=settings.font_file,
        raster_size_px=settings.glyph_raster_size_px,
        num_contour_points=settings.glyph_contour_num_points,
    )
    settings.contours_dir.mkdir(parents=True, exist_ok=True)
    glyphs: list[GlyphTarget] = []
    for glyph_form in GLYPH_FORMS:
        existing = await _existing_glyph(session, settings, glyph_form)
        if existing is not None:
            glyphs.append(existing)
            continue
        contours = extractor.extract(glyph_form)
        contour_path = settings.contours_dir / "live_smoke" / f"{glyph_form}.npz"
        contour_path.parent.mkdir(parents=True, exist_ok=True)
        save_contours(contour_path, contours)
        glyph = GlyphTarget(
            id=uuid4(),
            letter=BASE_LETTER_BY_GLYPH_FORM[glyph_form],
            glyph_form=glyph_form,
            font_name=settings.font_file.name,
            raster_size_px=settings.glyph_raster_size_px,
            contour_path=str(contour_path),
            num_points=sum(len(contour) for contour in contours),
            num_contours=len(contours),
        )
        session.add(GlyphTargetRow(**glyph.model_dump()))
        glyphs.append(glyph)
    await session.commit()
    return glyphs


async def _existing_glyph(session: AsyncSession, settings: BackendSettings, glyph_form: str) -> GlyphTarget | None:
    stmt = (
        select(GlyphTargetRow)
        .where(GlyphTargetRow.glyph_form == glyph_form)
        .where(GlyphTargetRow.font_name == settings.font_file.name)
        .where(GlyphTargetRow.raster_size_px == settings.glyph_raster_size_px)
        .order_by(GlyphTargetRow.id)
        .limit(1)
    )
    row = (await session.execute(stmt)).scalars().first()
    if row is None or not Path(row.contour_path).exists():
        return None
    return GlyphTarget.model_validate(row)


def _smoke_candidate(settings: BackendSettings) -> TransformCandidate:
    family = LissajousFamily()
    theta = _smoke_theta(settings)
    complexity = family.complexity(theta)
    return TransformCandidate(
        id=uuid4(),
        family=family.name(),
        theta=theta,
        shared_across_letters=True,
        interpretability_score=interpretability_score(
            complexity,
            settings.interpretability_prior_lissajous,
            settings.simplicity_c_scale,
        ),
        simplicity_score=simplicity_score(complexity, settings.simplicity_c_scale),
        mean_shape_distance=_SMOKE_MEAN_DISTANCE,
        lookup_ratio=_SMOKE_LOOKUP_RATIO,
        created_at=datetime.now(tz=UTC),
    )


def _smoke_theta(settings: BackendSettings) -> Theta:
    feature_count = settings.feature_n_mels + 4 + 4 * settings.feature_n_segments
    return {
        "freq_ratio_a": 1,
        "freq_ratio_b": 2,
        "affine_w": [0.0] * (3 * feature_count),
        "affine_b": [1.0, 0.0, 1.0],
    }


async def _seed_with_own_session(
    settings: BackendSettings,
) -> tuple[list[GlyphTarget], ExperimentRun, TransformCandidate]:
    engine = create_engine(settings.database_url)
    try:
        async with session_scope(engine) as session:
            return await seed_live_smoke_data(session, settings, ExperimentTracker(settings.experiments_dir))
    finally:
        await engine.dispose()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
