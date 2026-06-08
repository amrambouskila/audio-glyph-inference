"""Tests for src/simulation/batch_features.py."""

from __future__ import annotations

import numpy as np
import pytest
from src.simulation.audio_features import extract_features
from src.simulation.batch_features import compute_feature_matrix

SR = 16_000
FRAME = 512
N_MELS = 8
N_SEGMENTS = 3


def _audio_batch() -> list[np.ndarray]:
    rng = np.random.default_rng(0)
    return [rng.standard_normal((num_frames, FRAME)).astype(np.float64) for num_frames in [3, 5, 8, 3, 11, 4]]


def test_compute_feature_matrix_matches_scalar_extraction() -> None:
    audio = _audio_batch()
    phi = compute_feature_matrix(audio, sample_rate_hz=SR, n_mels=N_MELS, n_segments=N_SEGMENTS)
    expected = np.stack(
        [extract_features(frames, sample_rate_hz=SR, n_mels=N_MELS, n_segments=N_SEGMENTS) for frames in audio]
    )
    assert phi.shape == (len(audio), N_MELS + 4 + 4 * N_SEGMENTS)
    assert phi.dtype == np.float64
    assert np.isfinite(phi).all()
    np.testing.assert_allclose(phi, expected, atol=0.0, rtol=0.0)


def test_compute_feature_matrix_rejects_empty_batch() -> None:
    with pytest.raises(ValueError, match="at least one"):
        compute_feature_matrix([], sample_rate_hz=SR, n_mels=N_MELS, n_segments=N_SEGMENTS)


def test_compute_feature_matrix_rejects_too_few_frames() -> None:
    with pytest.raises(ValueError, match="at least 3 frames"):
        compute_feature_matrix(
            [np.zeros((2, FRAME), dtype=np.float64)],
            sample_rate_hz=SR,
            n_mels=N_MELS,
            n_segments=N_SEGMENTS,
        )
