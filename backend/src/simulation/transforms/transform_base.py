"""Base protocol for transform families F_θ.

A transform family is a parameterized function mapping a preprocessed
audio frame matrix to an ordered 2D contour. Concrete families live in
sibling modules (fourier_series.py, lissajous.py, ...).

Contract (sacred — see CLAUDE.md §3):
  - forward(audio, theta) -> ndarray of shape (N, 2), dtype=float64,
    unit-square coordinates in [-0.5, 0.5].
  - parameter_space() -> dict[str, tuple[float, float]] giving (low, high)
    search bounds for each θ component.
  - name() -> unique family identifier matching TransformCandidate.family.
"""
from __future__ import annotations

from typing import Protocol

import numpy as np


class TransformFamily(Protocol):
    """Protocol that every F_θ family must satisfy."""

    def name(self) -> str: ...

    def parameter_space(self) -> dict[str, tuple[float, float]]: ...

    def forward(
        self,
        audio: np.ndarray,
        theta: dict[str, float],
    ) -> np.ndarray: ...