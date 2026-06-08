"""Exercise `/ws/live` against the seeded catalog for every Hebrew glyph."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from uuid import UUID

import msgpack
import numpy as np
import websockets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import BackendSettings, get_settings
from src.constants import GLYPH_FORMS, TAU
from src.data.database import create_engine, session_scope
from src.data.orm.experiment_run_row import ExperimentRunRow
from src.data.orm.glyph_target_row import GlyphTargetRow

_DEFAULT_WEBSOCKET_URL = "ws://localhost:8000/ws/live"
_SYNTHETIC_TONE_HZ = 440.0
_SYNTHETIC_AMPLITUDE = 0.2
_PCM16_MAX = 32767.0


@dataclass(frozen=True)
class LiveSmokeTarget:
    """One candidate/glyph pair to exercise over the live WebSocket."""

    letter: str
    glyph_form: str
    glyph_target_id: UUID


@dataclass(frozen=True)
class LiveSmokeResult:
    """One successful live-loop smoke result."""

    letter: str
    glyph_form: str
    glyph_target_id: UUID
    shape_distance: float
    generated_points: int
    target_points: int


async def smoke_live_roundtrip(
    session: AsyncSession,
    settings: BackendSettings,
    websocket_url: str,
    candidate_id: UUID | None,
) -> list[LiveSmokeResult]:
    """Run one live configure/audio/score exchange for every available Hebrew glyph."""
    selected_candidate_id = candidate_id or await _latest_completed_candidate_id(session)
    targets = await _glyph_targets(session, settings)
    pcm16 = _synthetic_pcm16(
        settings.audio_sample_rate_hz,
        settings.audio_frame_length_samples,
        settings.audio_hop_length_samples,
        settings.feature_n_segments,
    )
    results: list[LiveSmokeResult] = []
    for target in targets:
        results.append(await _roundtrip_glyph(websocket_url, selected_candidate_id, target, settings, pcm16))
    return results


def main(argv: Sequence[str] | None = None) -> int:
    """Run the live all-glyph WebSocket smoke check."""
    parser = argparse.ArgumentParser(
        description="Smoke-test /ws/live for every catalog Hebrew glyph using a saved candidate.",
    )
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--websocket-url", default=_DEFAULT_WEBSOCKET_URL)
    parser.add_argument("--candidate-id", type=UUID, default=None)
    parser.add_argument("--font-file", type=Path, default=None)
    args = parser.parse_args(argv)

    settings = get_settings()
    overrides: dict[str, object] = {}
    if args.database_url is not None:
        overrides["database_url"] = args.database_url
    if args.font_file is not None:
        overrides["font_file"] = args.font_file
    if overrides:
        values = settings.model_dump()
        values.update(overrides)
        settings = BackendSettings(**values)

    results = asyncio.run(_smoke_with_own_session(settings, args.websocket_url, args.candidate_id))
    for result in results:
        print(
            f"{result.glyph_form}: d={result.shape_distance:.6f}, "
            f"generated={result.generated_points}, target={result.target_points}"
        )
    print(f"Live round-trip smoke passed for {len(results)} glyph targets.")
    return 0


async def _latest_completed_candidate_id(session: AsyncSession) -> UUID:
    stmt = (
        select(ExperimentRunRow.best_candidate_id)
        .where(ExperimentRunRow.completed_at.is_not(None))
        .where(ExperimentRunRow.best_candidate_id.is_not(None))
        .order_by(ExperimentRunRow.started_at.desc())
        .limit(1)
    )
    candidate_id = await session.scalar(stmt)
    if candidate_id is None:
        raise RuntimeError("no completed experiment run with a best_candidate_id was found")
    return candidate_id


async def _glyph_targets(session: AsyncSession, settings: BackendSettings) -> list[LiveSmokeTarget]:
    stmt = (
        select(GlyphTargetRow)
        .where(GlyphTargetRow.font_name == settings.font_file.name)
        .where(GlyphTargetRow.raster_size_px == settings.glyph_raster_size_px)
    )
    rows_by_glyph_form = {
        row.glyph_form: row
        for row in (await session.execute(stmt)).scalars()
        if row.glyph_form in GLYPH_FORMS and Path(row.contour_path).exists()
    }
    missing = [glyph_form for glyph_form in GLYPH_FORMS if glyph_form not in rows_by_glyph_form]
    if missing:
        raise RuntimeError(f"missing glyph targets for glyph forms: {', '.join(missing)}")
    return [
        LiveSmokeTarget(
            letter=rows_by_glyph_form[glyph_form].letter,
            glyph_form=glyph_form,
            glyph_target_id=rows_by_glyph_form[glyph_form].id,
        )
        for glyph_form in GLYPH_FORMS
    ]


async def _roundtrip_glyph(
    websocket_url: str,
    candidate_id: UUID,
    target: LiveSmokeTarget,
    settings: BackendSettings,
    pcm16: bytes,
) -> LiveSmokeResult:
    async with websockets.connect(websocket_url) as websocket:
        await websocket.send(
            _pack_message(
                {
                    "type": "configure",
                    "candidate_id": str(candidate_id),
                    "glyph_target_id": str(target.glyph_target_id),
                    "scoring_metric": "chamfer",
                }
            )
        )
        configured = _unpack_message(await websocket.recv())
        if configured != {
            "type": "configured",
            "candidate_id": str(candidate_id),
            "glyph_target_id": str(target.glyph_target_id),
        }:
            raise RuntimeError(f"{target.glyph_form}: configure failed with {configured}")
        await websocket.send(
            _pack_message(
                {
                    "type": "audio",
                    "sample_rate_hz": settings.audio_sample_rate_hz,
                    "pcm16": pcm16,
                }
            )
        )
        score = _unpack_message(await websocket.recv())
    return _validate_score(target, score)


def _validate_score(target: LiveSmokeTarget, score: dict[str, object]) -> LiveSmokeResult:
    if score.get("type") != "score":
        raise RuntimeError(f"{target.glyph_form}: expected score response, got {score}")
    distance = score.get("shape_distance")
    contours = score.get("contours")
    target_contours = score.get("target_contours")
    if not isinstance(distance, float) or not isfinite(distance):
        raise RuntimeError(f"{target.glyph_form}: shape_distance must be a finite float")
    if not isinstance(contours, list) or not isinstance(target_contours, list):
        raise RuntimeError(f"{target.glyph_form}: score response must include contour lists")
    if not contours or not target_contours:
        raise RuntimeError(f"{target.glyph_form}: score response contours must be non-empty")
    return LiveSmokeResult(
        letter=target.letter,
        glyph_form=target.glyph_form,
        glyph_target_id=target.glyph_target_id,
        shape_distance=distance,
        generated_points=len(contours),
        target_points=len(target_contours),
    )


def _pack_message(payload: dict[str, object]) -> bytes:
    return msgpack.packb(payload, use_bin_type=True)


def _unpack_message(data: bytes | str) -> dict[str, object]:
    if isinstance(data, str):
        raise RuntimeError("live smoke expected binary MessagePack response, got text")
    value = msgpack.unpackb(data, raw=False)
    if not isinstance(value, dict):
        raise RuntimeError("live smoke response must be a MessagePack map")
    return {str(key): item for key, item in value.items()}


def _synthetic_pcm16(
    sample_rate_hz: int,
    frame_length_samples: int,
    hop_length_samples: int,
    min_frames: int,
) -> bytes:
    sample_count = frame_length_samples + max(0, min_frames - 1) * hop_length_samples
    samples = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
    wave = _SYNTHETIC_AMPLITUDE * np.sin(TAU * _SYNTHETIC_TONE_HZ * samples)
    return np.clip(wave * _PCM16_MAX, -_PCM16_MAX, _PCM16_MAX).astype("<i2").tobytes()


async def _smoke_with_own_session(
    settings: BackendSettings,
    websocket_url: str,
    candidate_id: UUID | None,
) -> list[LiveSmokeResult]:
    engine = create_engine(settings.database_url)
    try:
        async with session_scope(engine) as session:
            return await smoke_live_roundtrip(session, settings, websocket_url, candidate_id)
    finally:
        await engine.dispose()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
