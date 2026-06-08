"""Tests for src/simulation/batch_synthesis.py."""

from __future__ import annotations

import numpy as np
from src.simulation.batch_features import compute_feature_matrix
from src.simulation.batch_procrustes import procrustes_distance_batch
from src.simulation.batch_synthesis import _normalize_batch, synthesize_fourier_batch, synthesize_lissajous_batch
from src.simulation.contour_compare import contour_compare
from src.simulation.transforms.fourier_series import FourierSeriesFamily
from src.simulation.transforms.lissajous import LissajousFamily

SR = 16_000
FRAME = 512
N_MELS = 8
N_SEGMENTS = 3
N_POINTS = 256
D = N_MELS + 4 + 4 * N_SEGMENTS


def _audio_batch() -> list[np.ndarray]:
    rng = np.random.default_rng(1)
    return [rng.standard_normal((num_frames, FRAME)).astype(np.float64) for num_frames in [3, 5, 8, 3, 11, 4]]


def test_normalize_batch_matches_unit_square_contract() -> None:
    raw = np.array(
        [
            [[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]],
            [[1.0, 1.0], [1.0, 1.0], [1.0, 1.0], [1.0, 1.0]],
        ],
        dtype=np.float64,
    )
    normalized = _normalize_batch(raw)
    np.testing.assert_allclose(normalized[0].mean(axis=0), [0.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(np.abs(normalized[0]).max(), 0.5, atol=1e-12)
    np.testing.assert_allclose(normalized[1], 0.0, atol=1e-12)


def test_synthesize_fourier_batch_locks_to_forward_and_scalar_distance() -> None:
    rng = np.random.default_rng(2)
    audio = _audio_batch()
    phi = compute_feature_matrix(audio, sample_rate_hz=SR, n_mels=N_MELS, n_segments=N_SEGMENTS)
    theta = {
        "rank_r": 2,
        "ridge_alpha": 0.1,
        "affine_u": rng.standard_normal(8 * 2).tolist(),
        "affine_v": rng.standard_normal(D * 2).tolist(),
        "affine_b": rng.standard_normal(8).tolist(),
    }
    batch = synthesize_fourier_batch(phi, theta, N_POINTS)
    scalar = np.stack([FourierSeriesFamily().forward(frames, theta) for frames in audio])
    assert np.isfinite(batch).all()
    np.testing.assert_allclose(batch, scalar, atol=1e-10, rtol=0.0)
    distances = procrustes_distance_batch(batch, scalar)
    expected = [contour_compare(batch[i], scalar[i], "procrustes") for i in range(len(audio))]
    assert np.isfinite(distances).all()
    np.testing.assert_allclose(distances, expected, atol=1e-10, rtol=0.0)


def test_synthesize_lissajous_batch_locks_to_forward_and_scalar_distance() -> None:
    rng = np.random.default_rng(3)
    audio = _audio_batch()
    phi = compute_feature_matrix(audio, sample_rate_hz=SR, n_mels=N_MELS, n_segments=N_SEGMENTS)
    theta = {
        "freq_ratio_a": 2,
        "freq_ratio_b": 3,
        "affine_w": rng.standard_normal(3 * D).tolist(),
        "affine_b": rng.standard_normal(3).tolist(),
    }
    batch = synthesize_lissajous_batch(phi, theta, N_POINTS)
    scalar = np.stack([LissajousFamily().forward(frames, theta) for frames in audio])
    assert np.isfinite(batch).all()
    np.testing.assert_allclose(batch, scalar, atol=1e-10, rtol=0.0)
    distances = procrustes_distance_batch(batch, scalar)
    expected = [contour_compare(batch[i], scalar[i], "procrustes") for i in range(len(audio))]
    assert np.isfinite(distances).all()
    np.testing.assert_allclose(distances, expected, atol=1e-10, rtol=0.0)
