"""Audio preprocessing: raw file -> framed, normalized 1D signal ready for transforms.

Steps: decode -> resample to config.audio_sample_rate_hz -> loudness-
normalize -> optional voice-activity trim -> frame into config.audio_frame_length_samples
with config.audio_hop_length_samples hop. Output is always a
numpy.ndarray of shape (num_frames, frame_length), dtype=float64,
units=normalized-amplitude.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


class AudioPreprocessor:
    """Standalone audio preprocessor; no API or DB dependencies."""

    def __init__(
        self,
        target_sample_rate_hz: int,
        frame_length_samples: int,
        hop_length_samples: int,
    ) -> None:
        raise NotImplementedError

    def load(self, path: Path) -> np.ndarray:
        """Load a raw audio file and return the preprocessed frame matrix.

        Returns:
            ndarray of shape (num_frames, frame_length), dtype=float64,
            units=normalized amplitude in [-1, 1].
        """
        raise NotImplementedError
