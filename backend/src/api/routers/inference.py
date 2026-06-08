"""One-shot inference endpoint."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_audio_preprocessor, get_session
from src.api.score_payload import validate_score_geometry, validated_score_payload
from src.data.orm.audio_sample_row import AudioSampleRow
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.paired_example_row import PairedExampleRow
from src.data.orm.transform_candidate_row import TransformCandidateRow
from src.models.inference_request import InferenceRequest
from src.models.inference_result import InferenceResult
from src.models.transform_candidate import TransformCandidate
from src.simulation.audio_preprocessor import AudioPreprocessor
from src.simulation.contour_compare import contour_compare
from src.simulation.contour_io import load_contours
from src.simulation.transforms.family_registry import build_family

router = APIRouter(prefix="/api/inference", tags=["inference"])


@router.post("", response_model=InferenceResult)
async def run_inference(
    body: InferenceRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    preprocessor: Annotated[AudioPreprocessor, Depends(get_audio_preprocessor)],
) -> InferenceResult:
    audio = await session.get(AudioSampleRow, body.audio_sample_id)
    candidate_row = await session.get(TransformCandidateRow, body.candidate_id)
    if audio is None or candidate_row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "audio_sample or candidate not found")
    glyph = await _glyph_for_audio(session, audio)
    if glyph is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "paired glyph target not found for audio sample")

    candidate = TransformCandidate.model_validate(candidate_row)
    family = build_family(candidate.family)
    frames = preprocessor.load(Path(audio.file_path)).frames
    generated = family.forward(frames, candidate.theta)
    target = np.vstack(load_contours(Path(glyph.contour_path))).astype(np.float64)
    try:
        validate_score_geometry(generated, target)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    distance = contour_compare(generated, target, body.scoring_metric)
    return _inference_result(generated, target, distance)


def _inference_result(generated: np.ndarray, target: np.ndarray, distance: float) -> InferenceResult:
    """Build a validated one-shot inference response.

    Args:
        generated: ndarray shape (num_points, 2) dtype=float64, units=unit-square coordinates [-0.5, 0.5].
        target: ndarray shape (num_points, 2) dtype=float64, units=unit-square coordinates [-0.5, 0.5].
        distance: shape-distance scalar in metric-specific normalized units.

    Returns:
        Validated one-shot inference response.
    """
    try:
        payload = validated_score_payload(generated, target, distance)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return InferenceResult(**payload)


async def _glyph_for_audio(session: AsyncSession, audio: AudioSampleRow) -> GlyphTargetRow | None:
    stmt = (
        select(GlyphTargetRow)
        .join(PairedExampleRow, PairedExampleRow.glyph_target_id == GlyphTargetRow.id)
        .where(PairedExampleRow.audio_sample_id == audio.id)
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()
