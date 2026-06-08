"""Fourier-series transform family F_θ (Phase 2 baseline).

Synthesizes a closed 2D contour from a low-order real trigonometric polynomial

    x(t) = Σ_{k=1..K} a_k cos(kt) + b_k sin(kt)
    y(t) = Σ_{k=1..K} c_k cos(kt) + d_k sin(kt),   t = linspace(0, 2π, N, endpoint=False)

whose 4K real coefficients come from a rank-r affine map of the audio feature
vector φ:  coeffs = U · (Vᵀ φ) + b. The real-linear coefficient form keeps the
audio→coeff map strictly affine (the anti-lookup capacity argument and the
exact-linearity test both depend on this).

θ has two tiers:
  - searched (declared in parameter_space): `rank_r`, `ridge_alpha`.
  - fitted (populated by SearchEngine's closed-form ridge fit, consumed here as
    list[float]): `affine_u` (flat 4K·r), `affine_v` (flat D·r), `affine_b` (4K).

The fitted vectors are NOT in parameter_space because ParameterSpec only
declares scalar search domains; they are produced by least squares, not searched
(see docs/phases/phase-2-plan.md §3.1/§5). K is read back from len(affine_b)//4;
D from the feature config — so forward stays a pure function of (audio, θ) and
config, with no external statistics.
"""

from __future__ import annotations

import numpy as np

from src.config import get_settings
from src.simulation.affine_fit import fit_fourier_theta
from src.simulation.audio_features import extract_features
from src.simulation.contour_normalize import normalize_to_unit_square
from src.simulation.transforms.parameter_spec import ParameterSpec
from src.simulation.transforms.transform_base import Theta


def _basis(n: int, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Closed trig-polynomial bases. Returns (cos, sin), each ndarray (n, k) float64."""
    t = 2.0 * np.pi * np.arange(n) / n
    angles = np.outer(t, np.arange(1, k + 1))
    return np.cos(angles), np.sin(angles)


def _synthesize(coeffs: np.ndarray, n: int) -> np.ndarray:
    """Map a length-4K real coefficient vector to a closed contour, linear in coeffs.

    Args:
        coeffs: ndarray (4K,) float64 = concat(a, b, c, d), each block length K.
        n: number of contour points.

    Returns:
        ndarray (n, 2) float64 raw (un-normalized) contour coordinates.
    """
    k = coeffs.size // 4
    a, b, c, d = coeffs.reshape(4, k)
    cos, sin = _basis(n, k)
    return np.stack([cos @ a + sin @ b, cos @ c + sin @ d], axis=1)


class FourierSeriesFamily:
    """F_θ where θ parameterizes a low-order closed Fourier contour via an affine map of φ."""

    def name(self) -> str:
        return "fourier_series"

    def parameter_space(self) -> dict[str, ParameterSpec]:
        return {
            "rank_r": ParameterSpec(kind="integer", low=1, high=3),
            "ridge_alpha": ParameterSpec(kind="continuous", low=1e-4, high=1.0),
        }

    def complexity(self, theta: Theta) -> float:
        """MDL-style cost: BITS·N_eff + struct·#keys + Σ log2(1+|coef|) + ORDER·K."""
        settings = get_settings()
        d = settings.feature_n_mels + 4 + 4 * settings.feature_n_segments
        rank_r = int(theta["rank_r"])
        k = len(theta["affine_b"]) // 4
        coeffs = np.concatenate(
            [np.asarray(theta["affine_u"]), np.asarray(theta["affine_v"]), np.asarray(theta["affine_b"])]
        )
        n_eff = rank_r * (4 * k + d) + 4 * k
        coef_cost = float(np.log2(1.0 + np.abs(coeffs)).sum())
        return (
            settings.complexity_bits_per_param * n_eff
            + settings.complexity_struct_cost * len(theta)
            + coef_cost
            + settings.complexity_order_penalty * k
        )

    def fit_theta(self, phi: np.ndarray, targets: np.ndarray, searched_theta: Theta, num_points: int) -> Theta:
        """Fit the rank-factored affine coefficient map.

        Args:
            phi: ndarray (B, D) float64, audio feature vectors.
            targets: ndarray (B, N, 2) float64, unit-square target contours.
            searched_theta: searched rank_r/ridge_alpha plus transient fourier_k.
            num_points: target contour point count N.

        Returns:
            theta with affine_u, affine_v, and affine_b list values.
        """
        return fit_fourier_theta(phi, targets, searched_theta, num_points)

    def forward(self, audio: np.ndarray, theta: Theta) -> np.ndarray:
        """Map preprocessed audio frames to a closed Fourier contour.

        Args:
            audio: ndarray (num_frames, frame_length) float64, normalized amplitude [-1, 1].
            theta: searched rank_r/ridge_alpha + fitted affine_u/affine_v/affine_b.

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
        rank_r = int(theta["rank_r"])
        b = np.asarray(theta["affine_b"], dtype=np.float64)
        u = np.asarray(theta["affine_u"], dtype=np.float64).reshape(b.size, rank_r)
        v = np.asarray(theta["affine_v"], dtype=np.float64).reshape(phi.size, rank_r)
        coeffs = u @ (v.T @ phi) + b
        return normalize_to_unit_square(_synthesize(coeffs, settings.glyph_contour_num_points))
