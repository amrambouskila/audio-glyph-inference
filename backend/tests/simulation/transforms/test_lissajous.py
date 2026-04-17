"""Tests for src/simulation/transforms/lissajous.py (Phase 2 scaffold)."""

from __future__ import annotations

import numpy as np
import pytest
from src.simulation.transforms.lissajous import LissajousFamily


def test_name_is_lissajous() -> None:
    assert LissajousFamily().name() == "lissajous"


def test_parameter_space_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        LissajousFamily().parameter_space()


def test_forward_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        LissajousFamily().forward(np.zeros((1, 4), dtype=np.float64), {})
