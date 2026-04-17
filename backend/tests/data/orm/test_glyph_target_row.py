"""Tests for src/data/orm/glyph_target_row.py."""

from __future__ import annotations

from src.data.orm.base import Base
from src.data.orm.glyph_target_row import GlyphTargetRow


def test_glyph_target_row_inherits_declarative_base() -> None:
    assert issubclass(GlyphTargetRow, Base)


def test_glyph_target_row_tablename() -> None:
    assert GlyphTargetRow.__tablename__ == "glyph_targets"
