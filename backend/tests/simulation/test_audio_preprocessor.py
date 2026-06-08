"""Tests for src/simulation/audio_preprocessor.py — real DSP, no mocking.

The DSP/validation branches are exercised on numpy-synthesized signals. WAV
decode is always covered; .m4a decode is smoke-tested when ffmpeg is available.
"""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf
from audioread.exceptions import NoBackendError
from src.simulation.audio_preprocessor import AudioPreprocessor
from src.simulation.audio_validation_error import AudioValidationError
from src.simulation.preprocess_result import PreprocessResult

from tests.conftest import FIXTURE_M4A

SR = 44_100


def _preprocessor() -> AudioPreprocessor:
    return AudioPreprocessor(
        target_sample_rate_hz=16_000,
        frame_length_samples=512,
        hop_length_samples=128,
        duration_min_s=1.0,
        duration_max_s=3.0,
        active_speech_min_s=0.4,
        active_speech_max_s=1.5,
        peak_dbfs_max=-1.0,
        target_lufs=-23.0,
        vad_top_db=30.0,
    )


def _tone(duration_s: float, amp: float = 0.3, sr: int = SR) -> np.ndarray:
    t = np.linspace(0.0, duration_s, int(sr * duration_s), endpoint=False)
    return (amp * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float64)


def _padded_tone(tone_s: float, pad_s: float, amp: float = 0.3, sr: int = SR) -> np.ndarray:
    pad = np.zeros(int(sr * pad_s), dtype=np.float64)
    return np.concatenate([pad, _tone(tone_s, amp, sr), pad])


def test_preprocess_valid_returns_frames() -> None:
    result = _preprocessor().preprocess(_padded_tone(tone_s=1.0, pad_s=0.5), SR)
    assert isinstance(result, PreprocessResult)
    assert result.frames.ndim == 2
    assert result.frames.shape[1] == 512
    assert result.frames.dtype == np.float64
    assert result.frames.min() >= -1.0
    assert result.frames.max() <= 1.0
    assert result.native_sample_rate_hz == SR
    assert 0.4 <= result.duration_s <= 1.5
    np.testing.assert_allclose(result.peak_dbfs, 20.0 * np.log10(0.3), atol=0.5)


def test_duration_too_short_rejected() -> None:
    with pytest.raises(AudioValidationError, match="duration"):
        _preprocessor().preprocess(_tone(0.5), SR)


def test_duration_too_long_rejected() -> None:
    with pytest.raises(AudioValidationError, match="duration"):
        _preprocessor().preprocess(_tone(4.0), SR)


def test_clipped_peak_rejected() -> None:
    with pytest.raises(AudioValidationError, match="clipped"):
        _preprocessor().preprocess(_tone(2.0, amp=1.0), SR)


def test_active_speech_too_short_rejected() -> None:
    with pytest.raises(AudioValidationError, match="active"):
        _preprocessor().preprocess(_padded_tone(tone_s=0.2, pad_s=0.9), SR)


def test_active_speech_too_long_rejected() -> None:
    with pytest.raises(AudioValidationError, match="active"):
        _preprocessor().preprocess(_tone(2.0), SR)


def test_load_decodes_and_preprocesses(tmp_path) -> None:
    wav = tmp_path / "sample.wav"
    sf.write(wav, _padded_tone(tone_s=1.0, pad_s=0.5), SR)
    result = _preprocessor().load(wav)
    assert isinstance(result, PreprocessResult)
    assert result.native_sample_rate_hz == SR
    assert result.frames.shape[1] == 512


def test_decode_m4a_fixture_when_backend_available() -> None:
    try:
        audio, sample_rate_hz = _preprocessor().decode(FIXTURE_M4A)
    except NoBackendError:
        pytest.skip("host ffmpeg/audioread backend is unavailable")
    assert audio.dtype == np.float64
    assert audio.ndim == 1
    assert sample_rate_hz == SR
