"""Tests for src/simulation/glyph_extractor.py — real font, no mocking."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from src import constants
from src.simulation.glyph_extractor import GlyphExtractor

FONT = Path(__file__).resolve().parents[2] / "data" / "fonts" / "StamAshkenazCLM.ttf"
RASTER = 256
NUM_POINTS = 256


@pytest.fixture(scope="module")
def extractor() -> GlyphExtractor:
    return GlyphExtractor(font_path=FONT, raster_size_px=RASTER, num_contour_points=NUM_POINTS)


@pytest.mark.parametrize("letter", list(constants.GLYPH_FORMS))
def test_extract_returns_unit_square_contours(extractor: GlyphExtractor, letter: str) -> None:
    contours = extractor.extract(letter)
    assert isinstance(contours, list)
    assert len(contours) >= 1
    for contour in contours:
        assert contour.ndim == 2
        assert contour.shape[1] == 2
        assert contour.dtype == np.float64

    stacked = np.vstack(contours)
    assert stacked.min() >= -0.5 - 1e-9
    assert stacked.max() <= 0.5 + 1e-9
    np.testing.assert_allclose(stacked.mean(axis=0), [0.0, 0.0], atol=1e-7)
    # total points stay near the configured budget (rounding slack ≤ one per contour)
    assert abs(stacked.shape[0] - NUM_POINTS) <= len(contours)


def test_detached_stroke_letters_have_two_contours(extractor: GlyphExtractor) -> None:
    # he and qof render with a detached stroke in this STAM font (empirically verified).
    assert len(extractor.extract("ה")) == 2
    assert len(extractor.extract("ק")) == 2


def test_single_component_letter_has_one_contour(extractor: GlyphExtractor) -> None:
    assert len(extractor.extract("א")) == 1
