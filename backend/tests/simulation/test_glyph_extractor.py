"""Tests for src/simulation/glyph_extractor.py (Phase 1 scaffold)."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.simulation.glyph_extractor import GlyphExtractor


def test_constructor_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        GlyphExtractor(
            font_path=Path("/app/data/fonts/StamAshkenazCLM.ttf"),
            raster_size_px=256,
            num_contour_points=256,
        )


def test_extract_is_scaffold_stub() -> None:
    instance = GlyphExtractor.__new__(GlyphExtractor)
    with pytest.raises(NotImplementedError):
        instance.extract("א")
