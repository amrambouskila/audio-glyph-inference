"""Tests for src/data/orm/glyph_target_row.py."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from src.data.orm.base import Base
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.models.glyph_target import GlyphTarget


def test_glyph_target_row_inherits_declarative_base() -> None:
    assert issubclass(GlyphTargetRow, Base)


def test_glyph_target_row_tablename() -> None:
    assert GlyphTargetRow.__tablename__ == "glyph_targets"


async def test_glyph_target_row_round_trips(db_session) -> None:
    row = GlyphTargetRow(
        id=uuid4(),
        letter="ב",
        glyph_form="ב",
        font_name="StamAshkenazCLM.ttf",
        raster_size_px=256,
        contour_path="/app/data/contours/bet.npz",
        num_points=256,
        num_contours=1,
    )
    db_session.add(row)
    await db_session.commit()

    fetched = (await db_session.execute(select(GlyphTargetRow).where(GlyphTargetRow.id == row.id))).scalar_one()
    model = GlyphTarget.model_validate(fetched)

    assert model.letter == "ב"
    assert model.glyph_form == "ב"
    assert model.font_name == "StamAshkenazCLM.ttf"
    assert model.num_points == 256
    assert model.num_contours == 1
