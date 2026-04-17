"""Tests for src/simulation/search_engine.py (Phase 2 scaffold)."""

from __future__ import annotations

import numpy as np
import pytest
from src.simulation.search_engine import SearchEngine


class _DummyFamily:
    def name(self) -> str:
        return "dummy"

    def parameter_space(self) -> dict[str, tuple[float, float]]:
        return {}

    def forward(self, audio, theta):
        return np.zeros((2, 2), dtype=np.float64)


def test_constructor_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        SearchEngine(
            family=_DummyFamily(),
            distance_metric="procrustes",
            strategy="grid",
            max_evaluations=10,
        )


def test_fit_is_scaffold_stub() -> None:
    engine = SearchEngine.__new__(SearchEngine)
    with pytest.raises(NotImplementedError):
        engine.fit(
            audio_batch=np.zeros((1, 2, 4), dtype=np.float64),
            target_batch=np.zeros((1, 2, 2), dtype=np.float64),
        )
