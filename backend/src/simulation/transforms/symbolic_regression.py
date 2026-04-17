"""Symbolic-regression-proposed transform family (Phase 3).

Uses PySR (optional dep, `.[symbolic]`) to search over explicit closed-
form expressions that map audio spectral features to contour Fourier
coefficients. Proposed expressions are then converted into standalone
TransformFamily instances.
"""

from __future__ import annotations

import numpy as np


class SymbolicRegressionFamily:
    """F_θ discovered by symbolic regression; θ = expression coefficients."""

    def name(self) -> str:
        return "symbolic_regression"

    def parameter_space(self) -> dict[str, tuple[float, float]]:
        raise NotImplementedError

    def forward(
        self,
        audio: np.ndarray,
        theta: dict[str, float],
    ) -> np.ndarray:
        raise NotImplementedError
