"""Tests for src/simulation/transforms/transform_base.py.

The TransformFamily Protocol declares the F_θ contract. Its method bodies
are `...` placeholders; to cover them we subclass the Protocol and invoke
super() from the concrete implementation (a valid no-op that executes the
ellipsis statement).
"""

from __future__ import annotations

import numpy as np
from src.simulation.transforms.parameter_spec import ParameterSpec
from src.simulation.transforms.transform_base import TransformFamily


class _ConcreteFamily(TransformFamily):
    def name(self) -> str:
        super().name()
        return "concrete"

    def parameter_space(self) -> dict[str, ParameterSpec]:
        super().parameter_space()
        return {"k": ParameterSpec(kind="continuous", low=0.0, high=1.0)}

    def complexity(self, theta) -> float:
        super().complexity(theta)
        return float(len(theta))

    def forward(self, audio: np.ndarray, theta) -> np.ndarray:
        super().forward(audio, theta)
        return np.zeros((4, 2), dtype=np.float64)


def test_protocol_methods_are_callable_via_super() -> None:
    family = _ConcreteFamily()
    assert family.name() == "concrete"
    assert family.parameter_space() == {"k": ParameterSpec(kind="continuous", low=0.0, high=1.0)}
    assert family.complexity({"k": 0.5}) == 1.0
    result = family.forward(np.zeros((1, 4), dtype=np.float64), {"k": 0.5})
    assert result.shape == (4, 2)
    assert result.dtype == np.float64
