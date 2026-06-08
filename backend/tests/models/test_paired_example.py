"""Tests for src/models/paired_example.py."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.models.paired_example import PairedExample


def _valid_payload() -> dict:
    return {
        "id": uuid4(),
        "audio_sample_id": uuid4(),
        "glyph_target_id": uuid4(),
        "letter": "ג",
        "pronunciation_variant": "hard",
        "glyph_form": "ג",
        "split": "train",
    }


def test_round_trip_preserves_fields() -> None:
    pair = PairedExample(**_valid_payload())
    rehydrated = PairedExample(**pair.model_dump())
    assert rehydrated == pair


def test_glyph_form_defaults_to_letter_for_legacy_payloads() -> None:
    payload = _valid_payload()
    del payload["glyph_form"]
    pair = PairedExample(**payload)
    assert pair.glyph_form == pair.letter


def test_missing_required_field_raises() -> None:
    payload = _valid_payload()
    del payload["split"]
    with pytest.raises(ValidationError):
        PairedExample(**payload)


def test_uuid_fields_are_distinct() -> None:
    pair = PairedExample(**_valid_payload())
    assert pair.audio_sample_id != pair.glyph_target_id


def test_invalid_split_rejected() -> None:
    payload = _valid_payload()
    payload["split"] = "holdout"
    with pytest.raises(ValidationError):
        PairedExample(**payload)


def test_invalid_letter_rejected() -> None:
    payload = _valid_payload()
    payload["letter"] = "X"
    with pytest.raises(ValidationError):
        PairedExample(**payload)


def test_invalid_glyph_form_rejected() -> None:
    payload = _valid_payload()
    payload["glyph_form"] = "Q"
    with pytest.raises(ValidationError):
        PairedExample(**payload)


def test_soft_variant_and_sofit_form_validate_against_base_letter() -> None:
    payload = _valid_payload()
    payload["letter"] = "כ"
    payload["pronunciation_variant"] = "soft"
    payload["glyph_form"] = "ך"
    pair = PairedExample(**payload)
    assert pair.pronunciation_variant == "soft"
    assert pair.glyph_form == "ך"


def test_invalid_variant_for_base_letter_rejected() -> None:
    payload = _valid_payload()
    payload["letter"] = "א"
    payload["pronunciation_variant"] = "hard"
    with pytest.raises(ValidationError):
        PairedExample(**payload)


def test_glyph_form_mismatch_rejected() -> None:
    payload = _valid_payload()
    payload["letter"] = "ב"
    payload["glyph_form"] = "ך"
    with pytest.raises(ValidationError):
        PairedExample(**payload)
