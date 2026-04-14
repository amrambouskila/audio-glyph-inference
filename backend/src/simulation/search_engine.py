"""Search engine: fit θ* = argmin_θ Σ d(F_θ(x_i), L_i).

Given a TransformFamily, a dataset slice of PairedExample, and a
shape-distance metric, returns a ranked list of candidate θ vectors.
Supports grid, CMA-ES, and Bayesian strategies; Phase 3 adds symbolic
regression as a proposal source.
"""
from __future__ import annotations

import numpy as np

from src.simulation.transforms.transform_base import TransformFamily


class SearchEngine:
    """Standalone transform search engine."""

    def __init__(
        self,
        family: TransformFamily,
        distance_metric: str,
        strategy: str,
        max_evaluations: int,
    ) -> None:
        raise NotImplementedError

    def fit(
        self,
        audio_batch: np.ndarray,
        target_batch: np.ndarray,
    ) -> list[dict[str, float]]:
        """Return candidates sorted best-first by mean shape distance.

        Args:
            audio_batch: (B, num_frames, frame_length) preprocessed audio.
            target_batch: (B, num_points, 2) target contours.
        """
        raise NotImplementedError