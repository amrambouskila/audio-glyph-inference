"""Lissajous transform family F_θ (Phase 2 baseline).

A pair of linearly parameterized coupled sinusoids

    x(t) = P · sin(a·t) + Q · cos(a·t)
    y(t) = R · sin(b·t),   t = linspace(0, 2π, N, endpoint=False)

with integer frequency ratios (a, b) and continuous shape drivers (P, Q, R).
This is equivalent to the amplitude/phase form `A_x·sin(a·t+δ)` with
`P=A_x·cos(δ)` and `Q=A_x·sin(δ)`, but the drivers are linear in the contour
and can therefore be fitted by closed-form least squares. The drivers come from
a small affine map of the audio feature vector φ (`drivers = W·φ + b0`, shared
across letters); a and b are global integer θ that cannot encode 22 letters.

θ tiers (see docs/phases/phase-2-plan.md §3.2):
  - searched (parameter_space): `freq_ratio_a`, `freq_ratio_b`.
  - fitted (list[float], from SearchEngine's least-squares fit): `affine_w`
    (flat 3·D), `affine_b` (3). D is read back from len(affine_w)//3.
"""

from __future__ import annotations

import numpy as np

from src.config import get_settings
from src.simulation.affine_fit import fit_lissajous_theta
from src.simulation.audio_features import extract_features
from src.simulation.contour_normalize import normalize_to_unit_square
from src.simulation.transforms.parameter_spec import ParameterSpec
from src.simulation.transforms.transform_base import Theta

_NUM_DRIVERS = 3  # (P, Q, R)


class LissajousFamily:
    """F_θ where θ parameterizes a two-oscillator Lissajous curve."""

    def name(self) -> str:
        return "lissajous"

    def parameter_space(self) -> dict[str, ParameterSpec]:
        return {
            "freq_ratio_a": ParameterSpec(kind="integer", low=1, high=5),
            "freq_ratio_b": ParameterSpec(kind="integer", low=1, high=5),
        }

    def complexity(self, theta: Theta) -> float:
        """Active affine entries plus the bit-cost of the two frequency ratios."""
        affine = np.concatenate([np.asarray(theta["affine_w"]), np.asarray(theta["affine_b"])])
        nnz = int(np.count_nonzero(affine))
        a = int(theta["freq_ratio_a"])
        b = int(theta["freq_ratio_b"])
        return float(nnz + np.log2(a) + np.log2(b))

    def fit_theta(self, phi: np.ndarray, targets: np.ndarray, searched_theta: Theta, num_points: int) -> Theta:
        """Fit the linear driver affine map.

        Args:
            phi: ndarray (B, D) float64, audio feature vectors.
            targets: ndarray (B, N, 2) float64, unit-square target contours.
            searched_theta: searched freq_ratio_a/freq_ratio_b theta.
            num_points: target contour point count N.

        Returns:
            theta with affine_w and affine_b list values.
        """
        return fit_lissajous_theta(phi, targets, searched_theta, num_points)

    def forward(self, audio: np.ndarray, theta: Theta) -> np.ndarray:
        """Map preprocessed audio frames to a closed Lissajous contour.

        Args:
            audio: ndarray (num_frames, frame_length) float64, normalized amplitude [-1, 1].
            theta: searched freq_ratio_a/freq_ratio_b + fitted affine_w/affine_b.

        Returns:
            ndarray (N, 2) float64 in [-0.5, 0.5], N = glyph_contour_num_points.
        """
        settings = get_settings()
        phi = extract_features(
            audio,
            sample_rate_hz=settings.audio_sample_rate_hz,
            n_mels=settings.feature_n_mels,
            n_segments=settings.feature_n_segments,
        )
        affine_b = np.asarray(theta["affine_b"], dtype=np.float64)
        w = np.asarray(theta["affine_w"], dtype=np.float64).reshape(_NUM_DRIVERS, phi.size)
        p, q, r = w @ phi + affine_b
        a = int(theta["freq_ratio_a"])
        b = int(theta["freq_ratio_b"])
        t = 2.0 * np.pi * np.arange(settings.glyph_contour_num_points) / settings.glyph_contour_num_points
        contour = np.stack([p * np.sin(a * t) + q * np.cos(a * t), r * np.sin(b * t)], axis=1)
        return normalize_to_unit_square(contour)
