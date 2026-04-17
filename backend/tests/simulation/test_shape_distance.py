"""Tests for src/simulation/shape_distance.py (Phase 1 scaffold).

Phase 2 replaces these scaffold assertions with numerical reference-value
tests per CLAUDE.md §13 ("Reference-value tests are mandatory").
"""

from __future__ import annotations

import numpy as np
import pytest
from src.simulation.shape_distance import (
    chamfer_distance,
    frechet_distance,
    procrustes_distance,
)


@pytest.mark.parametrize(
    "func",
    [procrustes_distance, frechet_distance, chamfer_distance],
)
def test_distance_functions_are_scaffold_stubs(func) -> None:
    a = np.zeros((4, 2), dtype=np.float64)
    b = np.ones((4, 2), dtype=np.float64)
    with pytest.raises(NotImplementedError):
        func(a, b)
