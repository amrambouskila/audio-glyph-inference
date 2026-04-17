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
        "split": "train",
    }


def test_round_trip_preserves_fields() -> None:
    pair = PairedExample(**_valid_payload())
    rehydrated = PairedExample(**pair.model_dump())
    assert rehydrated == pair


def test_missing_required_field_raises() -> None:
    payload = _valid_payload()
    del payload["split"]
    with pytest.raises(ValidationError):
        PairedExample(**payload)


def test_uuid_fields_are_distinct() -> None:
    pair = PairedExample(**_valid_payload())
    assert pair.audio_sample_id != pair.glyph_target_id
