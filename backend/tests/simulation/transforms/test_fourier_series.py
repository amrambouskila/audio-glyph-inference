"""Tests for src/simulation/transforms/fourier_series.py (Phase 2 scaffold)."""

from __future__ import annotations

import numpy as np
import pytest
from src.simulation.transforms.fourier_series import FourierSeriesFamily


def test_name_is_fourier_series() -> None:
    assert FourierSeriesFamily().name() == "fourier_series"


def test_parameter_space_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        FourierSeriesFamily().parameter_space()


def test_forward_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        FourierSeriesFamily().forward(np.zeros((1, 4), dtype=np.float64), {})
