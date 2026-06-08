"""Paired-example dataset ingestion and listing (Phase 1).

Endpoints:
  POST /api/datasets/audio    — upload a user-recorded .m4a (audio/mp4 | x-m4a | aac)
                                + form fields letter, accent, repetition; decoded +
                                validated via AudioPreprocessor (librosa+ffmpeg).
  POST /api/datasets/glyphs   — render + store a target glyph contour set (.npz).
  POST /api/datasets/pairs    — associate an AudioSample with a GlyphTarget.
  GET  /api/datasets/pairs    — list paired examples (filter by split / letter / accent).

Storage flow + validation rules follow docs/recording_protocol.md §7.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_audio_preprocessor,
    get_glyph_extractor,
    get_session,
    get_settings_dep,
)
from src.config import BackendSettings
from src.constants import (
    ACCENTS,
    ACCEPTED_AUDIO_MIME_TYPES,
    BASE_LETTER_BY_GLYPH_FORM,
    GLYPH_FORMS,
    HEBREW_LETTERS,
    PRONUNCIATION_VARIANT_PLAIN,
    PRONUNCIATION_VARIANTS_BY_BASE_LETTER,
)
from src.data.orm.audio_sample_row import AudioSampleRow
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.paired_example_row import PairedExampleRow
from src.models.audio_sample import AudioSample
from src.models.glyph_target import GlyphTarget
from src.models.paired_example import PairedExample
from src.models.paired_example_create import PairedExampleCreate
from src.simulation.audio_preprocessor import AudioPreprocessor
from src.simulation.audio_validation_error import AudioValidationError
from src.simulation.contour_io import save_contours
from src.simulation.glyph_extractor import GlyphExtractor

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("/audio", response_model=AudioSample, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    letter: Annotated[str, Form()],
    accent: Annotated[str, Form()],
    repetition: Annotated[int, Form()],
    file: Annotated[UploadFile, File()],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[BackendSettings, Depends(get_settings_dep)],
    preprocessor: Annotated[AudioPreprocessor, Depends(get_audio_preprocessor)],
    pronunciation_variant: Annotated[str, Form()] = PRONUNCIATION_VARIANT_PLAIN,
) -> AudioSample:
    if letter not in HEBREW_LETTERS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"unknown letter {letter!r}")
    if accent not in ACCENTS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"unknown accent {accent!r}")
    if repetition < 1:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "repetition must be >= 1")
    if pronunciation_variant not in PRONUNCIATION_VARIANTS_BY_BASE_LETTER[letter]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "pronunciation_variant is not valid for letter")
    if file.content_type not in ACCEPTED_AUDIO_MIME_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"unsupported media type {file.content_type!r}")

    data = await file.read()
    if len(data) > settings.audio_max_upload_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "file exceeds the upload size limit")

    timestamp = datetime.now(UTC)
    dest_dir = settings.audio_dir / accent / letter / pronunciation_variant
    dest_dir.mkdir(parents=True, exist_ok=True)
    m4a_path = dest_dir / f"{timestamp:%Y-%m-%d-%H%M%S}-rep{repetition}.m4a"
    m4a_path.write_bytes(data)

    try:
        result = preprocessor.load(m4a_path)
    except AudioValidationError as exc:
        m4a_path.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    sample = AudioSample(
        id=uuid4(),
        letter=letter,
        speaker_id=settings.audio_default_speaker_id,
        accent=accent,
        repetition=repetition,
        pronunciation_variant=pronunciation_variant,
        source="user",
        file_path=str(m4a_path),
        sample_rate_hz=result.native_sample_rate_hz,
        duration_s=result.duration_s,
        recorded_at=timestamp,
    )
    session.add(AudioSampleRow(**sample.model_dump()))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        m4a_path.unlink(missing_ok=True)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "duplicate take (speaker, accent, letter, pronunciation_variant, repetition)",
        ) from exc
    return sample


@router.post("/glyphs", response_model=GlyphTarget, status_code=status.HTTP_201_CREATED)
async def render_glyph(
    letter: Annotated[str, Query()],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[BackendSettings, Depends(get_settings_dep)],
    extractor: Annotated[GlyphExtractor, Depends(get_glyph_extractor)],
    glyph_form: Annotated[str | None, Query()] = None,
) -> GlyphTarget:
    if letter not in HEBREW_LETTERS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"unknown letter {letter!r}")
    resolved_glyph_form = glyph_form or letter
    if resolved_glyph_form not in GLYPH_FORMS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"unknown glyph_form {resolved_glyph_form!r}")
    if BASE_LETTER_BY_GLYPH_FORM[resolved_glyph_form] != letter:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "glyph_form does not match base letter")

    contours = extractor.extract(resolved_glyph_form)
    settings.contours_dir.mkdir(parents=True, exist_ok=True)
    contour_path = settings.contours_dir / f"{resolved_glyph_form}.npz"
    save_contours(contour_path, contours)

    glyph = GlyphTarget(
        id=uuid4(),
        letter=letter,
        glyph_form=resolved_glyph_form,
        font_name=settings.font_file.name,
        raster_size_px=settings.glyph_raster_size_px,
        contour_path=str(contour_path),
        num_points=sum(len(c) for c in contours),
        num_contours=len(contours),
    )
    session.add(GlyphTargetRow(**glyph.model_dump()))
    await session.commit()
    return glyph


@router.get("/glyphs", response_model=list[GlyphTarget])
async def list_glyphs(
    session: Annotated[AsyncSession, Depends(get_session)],
    letter: Annotated[str | None, Query()] = None,
    glyph_form: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[GlyphTarget]:
    if letter is not None and letter not in HEBREW_LETTERS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"unknown letter {letter!r}")
    if glyph_form is not None and glyph_form not in GLYPH_FORMS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"unknown glyph_form {glyph_form!r}")
    stmt = select(GlyphTargetRow)
    if letter is not None:
        stmt = stmt.where(GlyphTargetRow.letter == letter)
    if glyph_form is not None:
        stmt = stmt.where(GlyphTargetRow.glyph_form == glyph_form)
    stmt = (
        stmt.order_by(GlyphTargetRow.letter, GlyphTargetRow.glyph_form, GlyphTargetRow.id).limit(limit).offset(offset)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [GlyphTarget.model_validate(row) for row in rows]


@router.post("/pairs", response_model=PairedExample, status_code=status.HTTP_201_CREATED)
async def create_pair(
    body: PairedExampleCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PairedExample:
    audio = await session.get(AudioSampleRow, body.audio_sample_id)
    glyph = await session.get(GlyphTargetRow, body.glyph_target_id)
    if audio is None or glyph is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "audio_sample or glyph_target not found")
    if audio.letter != glyph.letter:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "letter mismatch between audio and glyph")

    pair = PairedExample(
        id=uuid4(),
        audio_sample_id=body.audio_sample_id,
        glyph_target_id=body.glyph_target_id,
        letter=audio.letter,
        pronunciation_variant=audio.pronunciation_variant,
        glyph_form=glyph.glyph_form,
        split=body.split,
    )
    session.add(PairedExampleRow(**pair.model_dump()))
    await session.commit()
    return pair


@router.get("/pairs", response_model=list[PairedExample])
async def list_pairs(
    session: Annotated[AsyncSession, Depends(get_session)],
    split: Annotated[str | None, Query()] = None,
    letter: Annotated[str | None, Query()] = None,
    pronunciation_variant: Annotated[str | None, Query()] = None,
    glyph_form: Annotated[str | None, Query()] = None,
    accent: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PairedExample]:
    stmt = select(PairedExampleRow)
    if split is not None:
        stmt = stmt.where(PairedExampleRow.split == split)
    if letter is not None:
        stmt = stmt.where(PairedExampleRow.letter == letter)
    if pronunciation_variant is not None:
        stmt = stmt.where(PairedExampleRow.pronunciation_variant == pronunciation_variant)
    if glyph_form is not None:
        stmt = stmt.where(PairedExampleRow.glyph_form == glyph_form)
    if accent is not None:
        stmt = stmt.join(AudioSampleRow, PairedExampleRow.audio_sample_id == AudioSampleRow.id).where(
            AudioSampleRow.accent == accent
        )
    stmt = stmt.order_by(PairedExampleRow.id).limit(limit).offset(offset)
    rows = (await session.execute(stmt)).scalars().all()
    return [PairedExample.model_validate(row) for row in rows]
