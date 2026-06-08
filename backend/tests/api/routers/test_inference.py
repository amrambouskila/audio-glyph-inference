"""Integration tests for src/api/routers/inference.py."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
import soundfile as sf
from fastapi import HTTPException
from src.api.routers.inference import _inference_result
from src.data.orm.audio_sample_row import AudioSampleRow
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.paired_example_row import PairedExampleRow
from src.data.orm.transform_candidate_row import TransformCandidateRow
from src.simulation.contour_io import save_contours

SR = 44_100
N_POINTS = 256
D_FEATURES = 24


def _tone(path: Path, frequency_hz: float) -> None:
    t = np.linspace(0.0, 1.0, int(SR * 1.0), endpoint=False)
    tone = 0.3 * np.sin(2.0 * np.pi * frequency_hz * t)
    pad = np.zeros(int(SR * 0.5), dtype=np.float64)
    signal = np.concatenate([pad, tone, pad])
    sf.write(path, signal, SR)


def _ellipse() -> np.ndarray:
    t = 2.0 * np.pi * np.arange(N_POINTS) / N_POINTS
    return np.stack([0.5 * np.cos(t), 0.25 * np.sin(t)], axis=1).astype(np.float64)


async def _seed_audio_pair(
    db_session,
    tmp_path: Path,
    *,
    repetition: int,
    frequency_hz: float,
    contour: np.ndarray | None = None,
) -> AudioSampleRow:
    audio_path = tmp_path / f"inference-{repetition}.wav"
    contour_path = tmp_path / f"inference-{repetition}.npz"
    _tone(audio_path, frequency_hz)
    save_contours(contour_path, [_ellipse() if contour is None else contour])
    audio = AudioSampleRow(
        id=uuid4(),
        letter=f"letter-{repetition}",
        speaker_id="owner",
        accent="ashkenazi",
        repetition=repetition,
        pronunciation_variant="plain",
        source="user",
        file_path=str(audio_path),
        sample_rate_hz=SR,
        duration_s=2.0,
        recorded_at=datetime(2026, 4, 16, tzinfo=UTC),
    )
    glyph = GlyphTargetRow(
        id=uuid4(),
        letter=audio.letter,
        glyph_form=audio.letter,
        font_name="StamAshkenazCLM.ttf",
        raster_size_px=256,
        contour_path=str(contour_path),
        num_points=N_POINTS,
        num_contours=1,
    )
    db_session.add_all([audio, glyph])
    await db_session.flush()
    db_session.add(
        PairedExampleRow(
            id=uuid4(),
            audio_sample_id=audio.id,
            glyph_target_id=glyph.id,
            letter=audio.letter,
            pronunciation_variant=audio.pronunciation_variant,
            glyph_form=glyph.glyph_form,
            split="train",
        )
    )
    await db_session.commit()
    return audio


async def _seed_unpaired_audio(db_session, tmp_path: Path, *, repetition: int, frequency_hz: float) -> AudioSampleRow:
    audio_path = tmp_path / f"unpaired-{repetition}.wav"
    _tone(audio_path, frequency_hz)
    audio = AudioSampleRow(
        id=uuid4(),
        letter=f"unpaired-{repetition}",
        speaker_id="owner",
        accent="ashkenazi",
        repetition=repetition,
        pronunciation_variant="plain",
        source="user",
        file_path=str(audio_path),
        sample_rate_hz=SR,
        duration_s=2.0,
        recorded_at=datetime(2026, 4, 16, tzinfo=UTC),
    )
    db_session.add(audio)
    await db_session.commit()
    return audio


def _candidate() -> TransformCandidateRow:
    w = np.zeros((3, D_FEATURES), dtype=np.float64)
    w[0, 0] = 0.05
    return TransformCandidateRow(
        id=uuid4(),
        family="lissajous",
        theta={
            "freq_ratio_a": 1,
            "freq_ratio_b": 1,
            "affine_w": w.reshape(-1).tolist(),
            "affine_b": [0.0, 1.0, 0.5],
        },
        expression=None,
        shared_across_letters=True,
        interpretability_score=0.7,
        simplicity_score=0.8,
        mean_shape_distance=0.2,
        lookup_ratio=0.3,
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )


async def test_inference_scores_audio_against_candidate(client, db_session, tmp_path) -> None:
    first = await _seed_audio_pair(db_session, tmp_path, repetition=1, frequency_hz=440.0)
    second = await _seed_audio_pair(db_session, tmp_path, repetition=2, frequency_hz=880.0)
    candidate = _candidate()
    db_session.add(candidate)
    await db_session.commit()

    first_resp = await client.post(
        "/api/inference",
        json={"audio_sample_id": str(first.id), "candidate_id": str(candidate.id), "scoring_metric": "procrustes"},
    )
    second_resp = await client.post(
        "/api/inference",
        json={"audio_sample_id": str(second.id), "candidate_id": str(candidate.id), "scoring_metric": "procrustes"},
    )

    assert first_resp.status_code == 200
    assert second_resp.status_code == 200
    assert len(first_resp.json()["contours"]) == N_POINTS
    assert len(first_resp.json()["target_contours"]) == N_POINTS
    assert first_resp.json()["shape_distance"] != second_resp.json()["shape_distance"]


async def test_inference_not_found_branches(client, db_session, tmp_path) -> None:
    audio = await _seed_audio_pair(db_session, tmp_path, repetition=1, frequency_hz=440.0)
    candidate = _candidate()
    db_session.add(candidate)
    await db_session.commit()

    missing_audio = await client.post(
        "/api/inference",
        json={"audio_sample_id": str(uuid4()), "candidate_id": str(candidate.id)},
    )
    missing_candidate = await client.post(
        "/api/inference",
        json={"audio_sample_id": str(audio.id), "candidate_id": str(uuid4())},
    )

    assert missing_audio.status_code == 404
    assert missing_candidate.status_code == 404


async def test_inference_requires_a_paired_glyph(client, db_session, tmp_path) -> None:
    audio = await _seed_unpaired_audio(db_session, tmp_path, repetition=3, frequency_hz=440.0)
    candidate = _candidate()
    db_session.add(candidate)
    await db_session.commit()

    resp = await client.post(
        "/api/inference",
        json={"audio_sample_id": str(audio.id), "candidate_id": str(candidate.id)},
    )

    assert resp.status_code == 404


async def test_inference_rejects_nonfinite_score_geometry(client, db_session, tmp_path) -> None:
    target = _ellipse()
    target[0, 0] = np.nan
    audio = await _seed_audio_pair(db_session, tmp_path, repetition=4, frequency_hz=440.0, contour=target)
    candidate = _candidate()
    db_session.add(candidate)
    await db_session.commit()

    resp = await client.post(
        "/api/inference",
        json={"audio_sample_id": str(audio.id), "candidate_id": str(candidate.id), "scoring_metric": "chamfer"},
    )

    assert resp.status_code == 422
    assert resp.json()["detail"] == "target contour coordinates must be finite"


def test_inference_result_rejects_nonfinite_distance() -> None:
    contour = _ellipse()

    with pytest.raises(HTTPException) as exc_info:
        _inference_result(contour, contour, np.nan)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "shape_distance must be finite"
