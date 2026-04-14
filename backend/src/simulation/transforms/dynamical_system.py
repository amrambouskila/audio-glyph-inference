"""PDE / ODE dynamical-system transform family (Phase 3).

A small parameterized ODE system is driven by the audio waveform as
input; the state trajectory projected to 2D is the output contour.
Candidate systems include Van der Pol, Duffing, and coupled resonators.
"""
from __future__ import annotations

import numpy as np


class DynamicalSystemFamily:
    """F_θ where θ parameterizes an ODE driven by audio input."""

    def name(self) -> str:
        return "dynamical_system"

    def parameter_space(self) -> dict[str, tuple[float, float]]:
        raise NotImplementedError

    def forward(
        self,
        audio: np.ndarray,
        theta: dict[str, float],
    ) -> np.ndarray:
        raise NotImplementedError