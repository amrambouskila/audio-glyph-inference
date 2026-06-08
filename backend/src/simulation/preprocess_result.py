"""PreprocessResult — output of AudioPreprocessor."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PreprocessResult:
    """Framed audio plus the measured metadata the AudioSample row records.

    frames: ndarray (num_frames, frame_length) dtype=float64, normalized amplitude in [-1, 1].
    native_sample_rate_hz: sample rate of the decoded file, before resampling.
    duration_s: final post-trim duration in seconds (the active speech span).
    peak_dbfs: peak amplitude of the raw decoded signal, in dBFS.
    """

    frames: np.ndarray
    native_sample_rate_hz: int
    duration_s: float
    peak_dbfs: float
