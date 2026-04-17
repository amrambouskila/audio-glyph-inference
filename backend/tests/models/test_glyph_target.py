"""Tests for src/models/glyph_target.py."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.models.glyph_target import GlyphTarget


def _valid_payload() -> dict:
    return {
        "id": uuid4(),
        "letter": "ב",
        "font_name": "StamAshkenazCLM.ttf",
        "raster_size_px": 256,
        "contour_path": "/app/data/contours/bet.npy",
        "num_points": 256,
    }


def test_round_trip_preserves_fields() -> None:
    glyph = GlyphTarget(**_valid_payload())
    rehydrated = GlyphTarget(**glyph.model_dump())
    assert rehydrated == glyph


def test_missing_required_field_raises() -> None:
    payload = _valid_payload()
    del payload["contour_path"]
    with pytest.raises(ValidationError):
        GlyphTarget(**payload)


def test_wrong_type_raises() -> None:
    payload = _valid_payload()
    payload["raster_size_px"] = "not-an-int"
    with pytest.raises(ValidationError):
        GlyphTarget(**payload)
