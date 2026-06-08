"""Batch audio feature extraction for SearchEngine fit entry."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from src.simulation.audio_features import extract_features


def compute_feature_matrix(
    audio: Sequence[np.ndarray],
    *,
    sample_rate_hz: int,
    n_mels: int,
    n_segments: int,
) -> np.ndarray:
    """Compute one feature vector per preprocessed audio sample.

    Args:
        audio: sequence length B of ndarrays (num_frames_i, frame_length) dtype=float64.

    Returns:
        ndarray (B, n_mels + 4 + 4*n_segments) dtype=float64.
    """
    if not audio:
        raise ValueError("audio batch must contain at least one sample")
    too_short = [frames.shape[0] for frames in audio if frames.shape[0] < n_segments]
    if too_short:
        raise ValueError(f"each sample must have at least {n_segments} frames; got {too_short}")
    return np.stack(
        [
            extract_features(
                frames,
                sample_rate_hz=sample_rate_hz,
                n_mels=n_mels,
                n_segments=n_segments,
            )
            for frames in audio
        ]
    ).astype(np.float64)
