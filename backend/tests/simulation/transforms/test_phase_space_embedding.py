"""Tests for src/simulation/transforms/phase_space_embedding.py (Phase 2 scaffold)."""

from __future__ import annotations

import numpy as np
import pytest
from src.simulation.transforms.phase_space_embedding import PhaseSpaceEmbeddingFamily


def test_name_is_phase_space_embedding() -> None:
    assert PhaseSpaceEmbeddingFamily().name() == "phase_space_embedding"


def test_parameter_space_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        PhaseSpaceEmbeddingFamily().parameter_space()


def test_forward_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        PhaseSpaceEmbeddingFamily().forward(np.zeros((1, 4), dtype=np.float64), {})
