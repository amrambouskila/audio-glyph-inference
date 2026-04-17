"""Tests for src/simulation/transforms/dynamical_system.py (Phase 3 scaffold)."""

from __future__ import annotations

import numpy as np
import pytest
from src.simulation.transforms.dynamical_system import DynamicalSystemFamily


def test_name_is_dynamical_system() -> None:
    assert DynamicalSystemFamily().name() == "dynamical_system"


def test_parameter_space_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        DynamicalSystemFamily().parameter_space()


def test_forward_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        DynamicalSystemFamily().forward(np.zeros((1, 4), dtype=np.float64), {})
