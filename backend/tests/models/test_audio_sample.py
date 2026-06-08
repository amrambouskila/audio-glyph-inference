"""Tests for src/models/audio_sample.py."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.models.audio_sample import AudioSample


def _valid_payload() -> dict:
    return {
        "id": uuid4(),
        "letter": "א",
        "speaker_id": "speaker-1",
        "accent": "ashkenazi",
        "repetition": 1,
        "pronunciation_variant": "plain",
        "source": "user",
        "file_path": "/app/data/audio/ashkenazi/א/2026-04-16-120000-rep1.m4a",
        "sample_rate_hz": 16_000,
        "duration_s": 1.5,
        "recorded_at": datetime(2026, 4, 16, 12, 0, 0, tzinfo=UTC),
    }


def test_round_trip_preserves_fields() -> None:
    sample = AudioSample(**_valid_payload())
    dumped = sample.model_dump()
    rehydrated = AudioSample(**dumped)
    assert rehydrated == sample


def test_missing_required_field_raises() -> None:
    payload = _valid_payload()
    del payload["letter"]
    with pytest.raises(ValidationError):
        AudioSample(**payload)


def test_wrong_type_raises() -> None:
    payload = _valid_payload()
    payload["sample_rate_hz"] = "not-a-number"
    with pytest.raises(ValidationError):
        AudioSample(**payload)


def test_all_accent_strings_accepted() -> None:
    for accent in ("ashkenazi", "sephardi", "moroccan", "yemenite", "chabad"):
        payload = _valid_payload()
        payload["accent"] = accent
        assert AudioSample(**payload).accent == accent


def test_invalid_letter_rejected() -> None:
    payload = _valid_payload()
    payload["letter"] = "Q"
    with pytest.raises(ValidationError):
        AudioSample(**payload)


def test_invalid_accent_rejected() -> None:
    payload = _valid_payload()
    payload["accent"] = "klingon"
    with pytest.raises(ValidationError):
        AudioSample(**payload)


def test_non_positive_repetition_rejected() -> None:
    payload = _valid_payload()
    payload["repetition"] = 0
    with pytest.raises(ValidationError):
        AudioSample(**payload)


def test_hard_soft_variants_accepted_for_begadkefat_letters() -> None:
    for variant in ("hard", "soft"):
        payload = _valid_payload()
        payload["letter"] = "ב"
        payload["pronunciation_variant"] = variant
        assert AudioSample(**payload).pronunciation_variant == variant


def test_hard_soft_variants_rejected_for_non_begadkefat_letters() -> None:
    payload = _valid_payload()
    payload["letter"] = "א"
    payload["pronunciation_variant"] = "hard"
    with pytest.raises(ValidationError):
        AudioSample(**payload)
