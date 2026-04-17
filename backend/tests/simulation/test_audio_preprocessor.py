"""Tests for src/simulation/audio_preprocessor.py (Phase 1 scaffold)."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.simulation.audio_preprocessor import AudioPreprocessor


def test_constructor_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        AudioPreprocessor(
            target_sample_rate_hz=16_000,
            frame_length_samples=512,
            hop_length_samples=128,
        )


def test_load_is_scaffold_stub() -> None:
    # Construct via __new__ to bypass the __init__ stub so we can reach .load.
    instance = AudioPreprocessor.__new__(AudioPreprocessor)
    with pytest.raises(NotImplementedError):
        instance.load(Path("/tmp/does-not-matter.m4a"))
