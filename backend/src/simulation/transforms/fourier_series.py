"""Fourier-series transform family (baseline candidate F_θ, Phase 2).

Maps the magnitude spectrum of the framed audio through a learned
low-order Fourier parameterization of a closed 2D contour:

    x(t) = sum_{k=1..K} a_k cos(k t + phi_k)
    y(t) = sum_{k=1..K} b_k sin(k t + psi_k)

with θ = {a_k, b_k, phi_k, psi_k, K}. The mapping from audio to θ is
affine in a handful of low-frequency cepstral moments; parameters are
shared across all letters unless explicitly per-letter fit.
"""

from __future__ import annotations

import numpy as np


class FourierSeriesFamily:
    """F_θ where θ parameterizes a low-order Fourier closed contour."""

    def name(self) -> str:
        return "fourier_series"

    def parameter_space(self) -> dict[str, tuple[float, float]]:
        raise NotImplementedError

    def forward(
        self,
        audio: np.ndarray,
        theta: dict[str, float],
    ) -> np.ndarray:
        raise NotImplementedError
