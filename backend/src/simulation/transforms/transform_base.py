"""Base protocol for transform families F_θ.

A transform family is a parameterized function mapping a preprocessed
audio frame matrix to an ordered 2D contour. Concrete families live in
sibling modules (fourier_series.py, lissajous.py, ...).

Contract (sacred — see CLAUDE.md §3):
  - forward(audio, theta) -> ndarray of shape (N, 2), dtype=float64,
    unit-square coordinates in [-0.5, 0.5].
  - parameter_space() -> dict[str, ParameterSpec] declaring the search
    domain of each θ component (continuous / integer / categorical).
  - complexity(theta) -> float: the Complexity(F_θ) term in the §2
    objective (lower is simpler), e.g. an MDL-like parameter cost.
  - name() -> unique family identifier matching TransformCandidate.family.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from src.simulation.transforms.parameter_spec import ParameterSpec

# θ value type — mirrors TransformCandidate.theta (master plan §3.5): families
# need ints (Fourier order K), coefficient lists, and categorical/symbolic tags.
Theta = dict[str, float | int | list[float] | str]


class TransformFamily(Protocol):
    """Protocol that every F_θ family must satisfy."""

    def name(self) -> str: ...

    def parameter_space(self) -> dict[str, ParameterSpec]: ...

    def complexity(self, theta: Theta) -> float: ...

    def forward(self, audio: np.ndarray, theta: Theta) -> np.ndarray: ...
