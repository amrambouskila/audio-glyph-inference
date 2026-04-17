"""Tests for src/simulation/transforms/symbolic_regression.py (Phase 3 scaffold)."""

from __future__ import annotations

import numpy as np
import pytest
from src.simulation.transforms.symbolic_regression import SymbolicRegressionFamily


def test_name_is_symbolic_regression() -> None:
    assert SymbolicRegressionFamily().name() == "symbolic_regression"


def test_parameter_space_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        SymbolicRegressionFamily().parameter_space()


def test_forward_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        SymbolicRegressionFamily().forward(np.zeros((1, 4), dtype=np.float64), {})
