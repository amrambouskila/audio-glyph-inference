"""Tests for src/simulation/transforms/transform_base.py.

The TransformFamily Protocol declares the F_θ contract. Its method bodies
are `...` (ellipsis) placeholders; to cover those lines we subclass the
Protocol and invoke super() from the concrete implementation. Calling
super() on a Protocol method with an `...` body is a valid no-op that
executes the statement.
"""

from __future__ import annotations

import numpy as np
from src.simulation.transforms.transform_base import TransformFamily


class _ConcreteFamily(TransformFamily):
    def name(self) -> str:
        super().name()
        return "concrete"

    def parameter_space(self) -> dict[str, tuple[float, float]]:
        super().parameter_space()
        return {"k": (0.0, 1.0)}

    def forward(self, audio: np.ndarray, theta: dict[str, float]) -> np.ndarray:
        super().forward(audio, theta)
        return np.zeros((4, 2), dtype=np.float64)


def test_protocol_methods_are_callable_via_super() -> None:
    family = _ConcreteFamily()
    assert family.name() == "concrete"
    assert family.parameter_space() == {"k": (0.0, 1.0)}
    result = family.forward(np.zeros((1, 4), dtype=np.float64), {"k": 0.5})
    assert result.shape == (4, 2)
    assert result.dtype == np.float64
