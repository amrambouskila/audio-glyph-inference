"""Tests for src/simulation/audio_features.py — closed-form / known-signal checks."""

from __future__ import annotations

import numpy as np
from src.simulation.audio_features import extract_features

SR = 16_000
FRAME = 512
HOP = 128
N_MELS = 8
N_SEG = 3
D = N_MELS + 4 + 4 * N_SEG


def _frames_from_signal(signal: np.ndarray) -> np.ndarray:
    count = 1 + (len(signal) - FRAME) // HOP
    return np.stack([signal[i * HOP : i * HOP + FRAME] for i in range(count)]).astype(np.float64)


def _tone(freq_hz: float, duration_s: float = 1.0) -> np.ndarray:
    t = np.arange(int(SR * duration_s)) / SR
    return 0.5 * np.sin(2.0 * np.pi * freq_hz * t)


def _phi(signal: np.ndarray) -> np.ndarray:
    return extract_features(_frames_from_signal(signal), sample_rate_hz=SR, n_mels=N_MELS, n_segments=N_SEG)


def test_feature_vector_shape_dtype_finite() -> None:
    phi = _phi(_tone(1000.0))
    assert phi.shape == (D,)
    assert phi.dtype == np.float64
    assert np.all(np.isfinite(phi))


def test_centroid_increases_with_tone_frequency() -> None:
    # global centroid is the first global descriptor, at index n_mels
    assert _phi(_tone(4000.0))[N_MELS] > _phi(_tone(500.0))[N_MELS]


def test_centroid_near_tone_frequency() -> None:
    np.testing.assert_allclose(_phi(_tone(1000.0))[N_MELS], 1000.0, atol=200.0)


def test_deterministic() -> None:
    frames = _frames_from_signal(_tone(1000.0))
    a = extract_features(frames, sample_rate_hz=SR, n_mels=N_MELS, n_segments=N_SEG)
    b = extract_features(frames, sample_rate_hz=SR, n_mels=N_MELS, n_segments=N_SEG)
    np.testing.assert_array_equal(a, b)


def test_short_live_window_keeps_segment_features_finite() -> None:
    frame = _frames_from_signal(_tone(1000.0, duration_s=0.04))[:1]
    phi = extract_features(frame, sample_rate_hz=SR, n_mels=N_MELS, n_segments=N_SEG)

    assert phi.shape == (D,)
    assert np.all(np.isfinite(phi))
