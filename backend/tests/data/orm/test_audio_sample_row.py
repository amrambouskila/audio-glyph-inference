"""Tests for src/data/orm/audio_sample_row.py."""

from __future__ import annotations

from src.data.orm.audio_sample_row import AudioSampleRow
from src.data.orm.base import Base


def test_audio_sample_row_inherits_declarative_base() -> None:
    assert issubclass(AudioSampleRow, Base)


def test_audio_sample_row_tablename() -> None:
    assert AudioSampleRow.__tablename__ == "audio_samples"
