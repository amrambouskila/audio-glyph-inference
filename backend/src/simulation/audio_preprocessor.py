"""Audio preprocessing: raw recording -> validated, framed, normalized signal.

Pipeline (docs/recording_protocol.md §3 + §7): decode -> validate duration +
peak -> resample to the target rate -> loudness-normalize (-LUFS) -> VAD-trim
leading/trailing silence -> validate active-speech span -> frame. Rejected
recordings raise AudioValidationError. Standalone; no API or DB dependency.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import pyloudnorm as pyln

from src.simulation.audio_validation_error import AudioValidationError
from src.simulation.preprocess_result import PreprocessResult

# Floor on peak amplitude so a silent signal does not log10(0) -> -inf.
_PEAK_FLOOR = 1e-12


class AudioPreprocessor:
    """Standalone audio preprocessor; no API or DB dependencies."""

    def __init__(
        self,
        *,
        target_sample_rate_hz: int,
        frame_length_samples: int,
        hop_length_samples: int,
        duration_min_s: float,
        duration_max_s: float,
        active_speech_min_s: float,
        active_speech_max_s: float,
        peak_dbfs_max: float,
        target_lufs: float,
        vad_top_db: float,
    ) -> None:
        self._sample_rate_hz = target_sample_rate_hz
        self._frame_length = frame_length_samples
        self._hop_length = hop_length_samples
        self._duration_min_s = duration_min_s
        self._duration_max_s = duration_max_s
        self._active_speech_min_s = active_speech_min_s
        self._active_speech_max_s = active_speech_max_s
        self._peak_dbfs_max = peak_dbfs_max
        self._target_lufs = target_lufs
        self._vad_top_db = vad_top_db

    def decode(self, path: Path) -> tuple[np.ndarray, int]:
        """Decode an audio file to mono float64 plus its native sample rate."""
        audio, native_sr = librosa.load(str(path), sr=None, mono=True)
        return audio.astype(np.float64), int(native_sr)

    def load(self, path: Path) -> PreprocessResult:
        """Decode a file and run the full preprocessing pipeline."""
        audio, native_sr = self.decode(path)
        return self.preprocess(audio, native_sr)

    def preprocess(self, audio: np.ndarray, native_sample_rate_hz: int) -> PreprocessResult:
        """Validate, resample, loudness-normalize, VAD-trim, and frame a decoded signal.

        Args:
            audio: 1D ndarray, dtype=float64, raw mono amplitude.
            native_sample_rate_hz: sample rate the signal was decoded at.

        Returns:
            PreprocessResult with frames (num_frames, frame_length) float64 in [-1, 1].
        """
        duration_s = len(audio) / native_sample_rate_hz
        if not self._duration_min_s <= duration_s <= self._duration_max_s:
            raise AudioValidationError(
                f"duration {duration_s:.2f}s outside [{self._duration_min_s}, {self._duration_max_s}]s"
            )

        peak_dbfs = 20.0 * np.log10(max(float(np.max(np.abs(audio))), _PEAK_FLOOR))
        if peak_dbfs > self._peak_dbfs_max:
            raise AudioValidationError(f"peak {peak_dbfs:.1f} dBFS exceeds {self._peak_dbfs_max} dBFS (clipped)")

        resampled = librosa.resample(audio, orig_sr=native_sample_rate_hz, target_sr=self._sample_rate_hz)
        loudness = pyln.Meter(self._sample_rate_hz).integrated_loudness(resampled)
        normalized = pyln.normalize.loudness(resampled, loudness, self._target_lufs)
        trimmed, _ = librosa.effects.trim(normalized, top_db=self._vad_top_db)

        active_speech_s = len(trimmed) / self._sample_rate_hz
        if not self._active_speech_min_s <= active_speech_s <= self._active_speech_max_s:
            raise AudioValidationError(
                f"active speech {active_speech_s:.2f}s outside "
                f"[{self._active_speech_min_s}, {self._active_speech_max_s}]s"
            )

        frames = librosa.util.frame(trimmed, frame_length=self._frame_length, hop_length=self._hop_length).T
        frames = np.clip(frames.astype(np.float64), -1.0, 1.0)
        return PreprocessResult(
            frames=frames,
            native_sample_rate_hz=native_sample_rate_hz,
            duration_s=active_speech_s,
            peak_dbfs=peak_dbfs,
        )
