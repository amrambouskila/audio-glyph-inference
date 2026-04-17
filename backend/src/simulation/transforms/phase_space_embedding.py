"""Phase-space (delay-embedding) transform family (Phase 2).

Uses Takens-style delay embedding of the 1D audio signal into a 2D
attractor manifold, with θ = {delay τ, gain, rotation, center}. The
projection to 2D is the output geometry.
"""

from __future__ import annotations

import numpy as np


class PhaseSpaceEmbeddingFamily:
    """F_θ where θ parameterizes a delay-embedding projection."""

    def name(self) -> str:
        return "phase_space_embedding"

    def parameter_space(self) -> dict[str, tuple[float, float]]:
        raise NotImplementedError

    def forward(
        self,
        audio: np.ndarray,
        theta: dict[str, float],
    ) -> np.ndarray:
        raise NotImplementedError
