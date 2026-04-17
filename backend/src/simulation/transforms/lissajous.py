"""Lissajous-style transform family (baseline candidate F_θ, Phase 2).

Parameterizes a pair of coupled oscillators whose frequency ratio,
phase offset, and amplitude envelope are extracted from the audio
spectrum. The output is the trajectory of the oscillator pair over one
period, normalized to the unit square.
"""

from __future__ import annotations

import numpy as np


class LissajousFamily:
    """F_θ where θ parameterizes a two-oscillator Lissajous curve."""

    def name(self) -> str:
        return "lissajous"

    def parameter_space(self) -> dict[str, tuple[float, float]]:
        raise NotImplementedError

    def forward(
        self,
        audio: np.ndarray,
        theta: dict[str, float],
    ) -> np.ndarray:
        raise NotImplementedError
