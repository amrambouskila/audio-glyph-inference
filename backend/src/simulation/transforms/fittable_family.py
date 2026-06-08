"""Optional protocol for families whose fitted theta is produced by closed-form least squares."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from src.simulation.transforms.transform_base import Theta


@runtime_checkable
class FittableFamily(Protocol):
    """Transform families that can fit non-searched theta from feature/target batches."""

    def fit_theta(
        self,
        phi: np.ndarray,
        targets: np.ndarray,
        searched_theta: Theta,
        num_points: int,
    ) -> Theta:
        """Fit theta from a feature matrix and target contours.

        Args:
            phi: ndarray (B, D) dtype=float64, audio feature vectors.
            targets: ndarray (B, N, 2) dtype=float64, unit-square target contours.
            searched_theta: scalar searched theta keys from parameter_space().
            num_points: target contour point count N.

        Returns:
            theta with searched keys plus fitted vector/list values.
        """
        ...
