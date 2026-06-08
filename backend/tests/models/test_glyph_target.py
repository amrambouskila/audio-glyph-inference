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
        "glyph_form": "ב",
        "font_name": "StamAshkenazCLM.ttf",
        "raster_size_px": 256,
        "contour_path": "/app/data/contours/bet.npz",
        "num_points": 256,
        "num_contours": 1,
    }


def test_round_trip_preserves_fields() -> None:
    glyph = GlyphTarget(**_valid_payload())
    rehydrated = GlyphTarget(**glyph.model_dump())
    assert rehydrated == glyph


def test_glyph_form_defaults_to_letter_for_legacy_payloads() -> None:
    payload = _valid_payload()
    del payload["glyph_form"]
    glyph = GlyphTarget(**payload)
    assert glyph.glyph_form == glyph.letter


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


def test_invalid_letter_rejected() -> None:
    payload = _valid_payload()
    payload["letter"] = "Z"
    with pytest.raises(ValidationError):
        GlyphTarget(**payload)


def test_invalid_glyph_form_rejected() -> None:
    payload = _valid_payload()
    payload["glyph_form"] = "Q"
    with pytest.raises(ValidationError):
        GlyphTarget(**payload)


def test_sofit_glyph_form_maps_to_base_letter() -> None:
    payload = _valid_payload()
    payload["letter"] = "כ"
    payload["glyph_form"] = "ך"
    assert GlyphTarget(**payload).glyph_form == "ך"


def test_glyph_form_must_match_base_letter() -> None:
    payload = _valid_payload()
    payload["letter"] = "ב"
    payload["glyph_form"] = "ך"
    with pytest.raises(ValidationError):
        GlyphTarget(**payload)
