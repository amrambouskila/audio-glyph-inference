"""Audio feature extraction: framed signal -> a small feature vector φ for the F_θ families.

Pure NumPy/SciPy (never librosa in this path). φ deliberately RETAINS temporal/transient
structure (per-segment spectral descriptors) so it is not a clean phoneme label — see the
anti-lookup design in docs/phases/phase-2-plan.md §2. Standardization of φ is folded into the
fitted affine map (not applied here), so this stays a pure function of (frames, config).
"""

from __future__ import annotations

import numpy as np

_EPS = 1e-12


def _hz_to_mel(hz: np.ndarray | float) -> np.ndarray | float:
    return 2595.0 * np.log10(1.0 + np.asarray(hz) / 700.0)


def _mel_to_hz(mel: np.ndarray) -> np.ndarray:
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def _mel_filterbank(n_mels: int, frame_length: int, sample_rate_hz: int) -> np.ndarray:
    """Triangular mel filterbank, shape (n_mels, n_bins), built vectorized (no per-filter loop)."""
    freqs = np.fft.rfftfreq(frame_length, d=1.0 / sample_rate_hz)
    edges = _mel_to_hz(np.linspace(_hz_to_mel(0.0), _hz_to_mel(sample_rate_hz / 2.0), n_mels + 2))
    lower, center, upper = edges[:-2, None], edges[1:-1, None], edges[2:, None]
    f = freqs[None, :]
    rising = (f - lower) / (center - lower)
    falling = (upper - f) / (upper - center)
    return np.clip(np.minimum(rising, falling), 0.0, None)


def _spectral_descriptors(power: np.ndarray, freqs: np.ndarray) -> np.ndarray:
    """Mean over frames of (centroid, bandwidth, 85%-rolloff, flatness). power: (num_frames, n_bins)."""
    total = power.sum(axis=1) + _EPS
    centroid = (power @ freqs) / total
    bandwidth = np.sqrt(np.clip((power @ (freqs**2)) / total - centroid**2, 0.0, None))
    cumulative = np.cumsum(power, axis=1)
    rolloff = freqs[(cumulative < 0.85 * cumulative[:, -1:]).sum(axis=1).clip(0, freqs.size - 1)]
    geometric_mean = np.exp(np.log(power + _EPS).mean(axis=1))
    flatness = geometric_mean / (power.mean(axis=1) + _EPS)
    return np.array([centroid.mean(), bandwidth.mean(), rolloff.mean(), flatness.mean()], dtype=np.float64)


def _segment_descriptors(power: np.ndarray, freqs: np.ndarray, n_segments: int) -> np.ndarray:
    """Per-segment descriptors; empty short-window segments reuse the nearest available frame."""
    segments = np.array_split(power, n_segments, axis=0)
    filled_segments = [
        segment if segment.shape[0] > 0 else power[min(index, power.shape[0] - 1) : min(index, power.shape[0] - 1) + 1]
        for index, segment in enumerate(segments)
    ]
    return np.concatenate([_spectral_descriptors(segment, freqs) for segment in filled_segments])


def extract_features(frames: np.ndarray, *, sample_rate_hz: int, n_mels: int, n_segments: int) -> np.ndarray:
    """Feature vector φ for the transform families.

    Args:
        frames: ndarray (num_frames, frame_length) dtype=float64, normalized amplitude in [-1, 1].

    Returns:
        ndarray shape (n_mels + 4 + 4*n_segments,) dtype=float64:
        [log-mel means | global spectral descriptors | per-time-segment spectral descriptors].
    """
    frame_length = frames.shape[1]
    window = np.hanning(frame_length)
    power = np.abs(np.fft.rfft(frames * window, axis=1)) ** 2
    freqs = np.fft.rfftfreq(frame_length, d=1.0 / sample_rate_hz)

    log_mel = np.log(power @ _mel_filterbank(n_mels, frame_length, sample_rate_hz).T + _EPS).mean(axis=0)
    global_descriptors = _spectral_descriptors(power, freqs)
    segment_descriptors = _segment_descriptors(power, freqs, n_segments)
    return np.concatenate([log_mel, global_descriptors, segment_descriptors]).astype(np.float64)
