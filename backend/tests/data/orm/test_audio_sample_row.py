"""Tests for src/data/orm/audio_sample_row.py."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.data.orm.audio_sample_row import AudioSampleRow
from src.data.orm.base import Base
from src.models.audio_sample import AudioSample


def _row(**overrides) -> AudioSampleRow:
    fields = {
        "id": uuid4(),
        "letter": "א",
        "speaker_id": "owner",
        "accent": "ashkenazi",
        "repetition": 1,
        "pronunciation_variant": "plain",
        "source": "user",
        "file_path": "/app/data/audio/ashkenazi/א/2026-04-16-120000-rep1.m4a",
        "sample_rate_hz": 16_000,
        "duration_s": 1.5,
        "recorded_at": datetime(2026, 4, 16, 12, 0, 0, tzinfo=UTC),
    }
    fields.update(overrides)
    return AudioSampleRow(**fields)


def test_audio_sample_row_inherits_declarative_base() -> None:
    assert issubclass(AudioSampleRow, Base)


def test_audio_sample_row_tablename() -> None:
    assert AudioSampleRow.__tablename__ == "audio_samples"


async def test_audio_sample_row_round_trips(db_session) -> None:
    row = _row()
    db_session.add(row)
    await db_session.commit()

    fetched = (await db_session.execute(select(AudioSampleRow).where(AudioSampleRow.id == row.id))).scalar_one()
    model = AudioSample.model_validate(fetched)

    assert model.letter == "א"
    assert model.accent == "ashkenazi"
    assert model.repetition == 1
    assert model.pronunciation_variant == "plain"
    assert model.sample_rate_hz == 16_000


async def test_audio_sample_unique_take_constraint(db_session) -> None:
    db_session.add(_row())
    await db_session.commit()

    db_session.add(_row())  # same (speaker_id, accent, letter, repetition), new id
    with pytest.raises(IntegrityError):
        await db_session.commit()
