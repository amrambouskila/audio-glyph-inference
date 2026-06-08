"""Tests for src/data/orm/paired_example_row.py."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from src.data.orm.audio_sample_row import AudioSampleRow
from src.data.orm.base import Base
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.paired_example_row import PairedExampleRow
from src.models.paired_example import PairedExample


def test_paired_example_row_inherits_declarative_base() -> None:
    assert issubclass(PairedExampleRow, Base)


def test_paired_example_row_tablename() -> None:
    assert PairedExampleRow.__tablename__ == "paired_examples"


async def test_paired_example_row_round_trips_with_fks(db_session) -> None:
    audio = AudioSampleRow(
        id=uuid4(),
        letter="ג",
        speaker_id="owner",
        accent="ashkenazi",
        repetition=1,
        pronunciation_variant="hard",
        source="user",
        file_path="/app/data/audio/ashkenazi/ג/x-rep1.m4a",
        sample_rate_hz=16_000,
        duration_s=1.5,
        recorded_at=datetime(2026, 4, 16, 12, 0, 0, tzinfo=UTC),
    )
    glyph = GlyphTargetRow(
        id=uuid4(),
        letter="ג",
        glyph_form="ג",
        font_name="StamAshkenazCLM.ttf",
        raster_size_px=256,
        contour_path="/app/data/contours/gimel.npz",
        num_points=256,
        num_contours=1,
    )
    db_session.add_all([audio, glyph])
    await db_session.commit()

    pair = PairedExampleRow(
        id=uuid4(),
        audio_sample_id=audio.id,
        glyph_target_id=glyph.id,
        letter="ג",
        pronunciation_variant="hard",
        glyph_form="ג",
        split="train",
    )
    db_session.add(pair)
    await db_session.commit()

    fetched = (await db_session.execute(select(PairedExampleRow).where(PairedExampleRow.id == pair.id))).scalar_one()
    model = PairedExample.model_validate(fetched)

    assert model.letter == "ג"
    assert model.split == "train"
    assert model.pronunciation_variant == "hard"
    assert model.glyph_form == "ג"
    assert model.audio_sample_id == audio.id
    assert model.glyph_target_id == glyph.id
