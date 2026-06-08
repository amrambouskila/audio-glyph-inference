"""Symbolic-regression transform family (Phase 3)."""

from __future__ import annotations

import numpy as np

from src.config import get_settings
from src.simulation.audio_features import extract_features
from src.simulation.contour_normalize import normalize_to_unit_square
from src.simulation.symbolic_expression import evaluate_symbolic_expression
from src.simulation.transforms.fourier_series import _synthesize
from src.simulation.transforms.parameter_spec import ParameterSpec
from src.simulation.transforms.transform_base import Theta


class SymbolicRegressionFamily:
    """F_theta whose Fourier coefficients are explicit symbolic expressions of audio features."""

    def name(self) -> str:
        return "symbolic_regression"

    def parameter_space(self) -> dict[str, ParameterSpec]:
        return {}

    def complexity(self, theta: Theta) -> float:
        """Symbolic MDL proxy from expression count, expression text length, and Fourier order."""
        settings = get_settings()
        expressions = _coefficient_expressions(theta)
        expression_cost = float(sum(np.log2(1.0 + len(expression)) for expression in expressions))
        order = int(theta["fourier_k"])
        return (
            settings.complexity_bits_per_param * len(expressions)
            + settings.complexity_struct_cost * len(theta)
            + settings.complexity_order_penalty * order
            + expression_cost
        )

    def forward(self, audio: np.ndarray, theta: Theta) -> np.ndarray:
        """Map audio frames to a symbolic-regression Fourier contour.

        Args:
            audio: ndarray (num_frames, frame_length) float64, normalized amplitude [-1, 1].
            theta: fourier_k plus coeff_0..coeff_(4K-1) expression strings over f0..fD.

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
        coeffs = np.asarray(
            [evaluate_symbolic_expression(expression, phi) for expression in _coefficient_expressions(theta)],
            dtype=np.float64,
        )
        return normalize_to_unit_square(_synthesize(coeffs, settings.glyph_contour_num_points))


def _coefficient_expressions(theta: Theta) -> list[str]:
    if "fourier_k" not in theta:
        raise ValueError("symbolic theta requires fourier_k")
    order = int(theta["fourier_k"])
    if order <= 0:
        raise ValueError("fourier_k must be positive")
    expressions: list[str] = []
    for index in range(4 * order):
        value = theta.get(f"coeff_{index}")
        if not isinstance(value, str):
            raise ValueError(f"symbolic theta requires string coeff_{index}")
        expressions.append(value)
    return expressions
