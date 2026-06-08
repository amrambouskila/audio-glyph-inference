"""Phase-space (delay-embedding) transform family F_θ (Phase 2 baseline).

Reconstructs the 1D signal from the overlap-framed audio, standardizes it, and
Takens-embeds it into 2D with delay τ, then applies a rigid placement
(gain · R(rotation) · (P − center)) and arc-length resamples to N points.

Unlike the Fourier/Lissajous families there is NO learned audio→parameter map:
θ is pure geometric placement, so this family structurally cannot memorize a
per-letter lookup. It is the least expressive baseline and the most likely
honest negative result (acceptable per the master plan).

θ keys (all searched — see docs/phases/phase-2-plan.md §3.3):
  `tau` (int), `gain`, `rotation`, `center_x`, `center_y` (continuous).
"""

from __future__ import annotations

import numpy as np

from src.config import get_settings
from src.constants import PI
from src.simulation.contour_resample import resample_closed
from src.simulation.transforms.parameter_spec import ParameterSpec
from src.simulation.transforms.transform_base import Theta

_STD_EPS = 1e-12


def _reconstruct_signal(frames: np.ndarray, hop: int) -> np.ndarray:
    """Overlap-trim framed audio back to 1D: hop fresh samples per frame + last frame's tail.

    Args:
        frames: ndarray (num_frames, frame_length) float64.
        hop: hop length in samples used when the frames were cut.

    Returns:
        ndarray (L,) float64, L = (num_frames-1)*hop + frame_length.
    """
    if frames.shape[0] == 1:
        return frames[0].astype(np.float64)
    return np.concatenate([frames[:-1, :hop].reshape(-1), frames[-1]]).astype(np.float64)


def _standardize(signal: np.ndarray) -> np.ndarray:
    """Zero-mean, unit-variance; a constant signal is returned mean-removed (no divide-by-zero)."""
    centered = signal - signal.mean()
    std = float(centered.std())
    return centered / std if std > _STD_EPS else centered


def _embed(signal: np.ndarray, tau: int) -> np.ndarray:
    """Takens 2D delay embedding. Returns ndarray (L-τ, 2) float64 = [s[:-τ], s[τ:]]."""
    return np.stack([signal[:-tau], signal[tau:]], axis=1)


def _rigid(points: np.ndarray, gain: float, rotation: float, center: np.ndarray) -> np.ndarray:
    """Apply gain · R(rotation) · (points − center). Returns ndarray (M, 2) float64."""
    cos, sin = np.cos(rotation), np.sin(rotation)
    rot = np.array([[cos, -sin], [sin, cos]], dtype=np.float64)
    return gain * ((points - center) @ rot.T)


class PhaseSpaceEmbeddingFamily:
    """F_θ where θ parameterizes a Takens delay-embedding projection."""

    def name(self) -> str:
        return "phase_space_embedding"

    def parameter_space(self) -> dict[str, ParameterSpec]:
        return {
            "tau": ParameterSpec(kind="integer", low=1, high=64),
            "gain": ParameterSpec(kind="continuous", low=0.05, high=2.0),
            "rotation": ParameterSpec(kind="continuous", low=-PI, high=PI),
            "center_x": ParameterSpec(kind="continuous", low=-0.5, high=0.5),
            "center_y": ParameterSpec(kind="continuous", low=-0.5, high=0.5),
        }

    def complexity(self, theta: Theta) -> float:
        """Parameter count plus the bit-cost of the delay τ (longer delays cost more)."""
        return float(len(self.parameter_space()) + np.log2(1.0 + int(theta["tau"])))

    def forward(self, audio: np.ndarray, theta: Theta) -> np.ndarray:
        """Map preprocessed audio frames to a closed phase-space contour.

        Args:
            audio: ndarray (num_frames, frame_length) float64, normalized amplitude [-1, 1].
            theta: tau / gain / rotation / center_x / center_y.

        Returns:
            ndarray (N, 2) float64 in [-0.5, 0.5], N = glyph_contour_num_points.
        """
        settings = get_settings()
        signal = _standardize(_reconstruct_signal(audio, settings.audio_hop_length_samples))
        tau = max(1, min(int(theta["tau"]), signal.size - 2))
        center = np.array([float(theta["center_x"]), float(theta["center_y"])], dtype=np.float64)
        mapped = _rigid(_embed(signal, tau), float(theta["gain"]), float(theta["rotation"]), center)
        n = settings.glyph_contour_num_points
        extent = float(np.abs(mapped - mapped.mean(axis=0)).max())
        resampled = resample_closed(mapped, n) if extent > _STD_EPS else np.repeat(mapped[:1], n, axis=0)
        return np.clip(resampled, -0.5, 0.5)
