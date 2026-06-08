"""Tests for src/simulation/transforms/family_registry.py."""

from __future__ import annotations

import pytest
from src.config import BackendSettings
from src.simulation.transforms.dynamical_system import DynamicalSystemFamily
from src.simulation.transforms.family_registry import FAMILY_REGISTRY, build_family
from src.simulation.transforms.fourier_series import FourierSeriesFamily
from src.simulation.transforms.lissajous import LissajousFamily
from src.simulation.transforms.phase_space_embedding import PhaseSpaceEmbeddingFamily
from src.simulation.transforms.symbolic_regression import SymbolicRegressionFamily


def test_registry_contains_phase_two_families() -> None:
    assert FAMILY_REGISTRY == {
        "fourier_series": FourierSeriesFamily,
        "lissajous": LissajousFamily,
        "phase_space_embedding": PhaseSpaceEmbeddingFamily,
        "dynamical_system": DynamicalSystemFamily,
        "symbolic_regression": SymbolicRegressionFamily,
    }


@pytest.mark.parametrize(
    ("name", "family_type"),
    [
        ("fourier_series", FourierSeriesFamily),
        ("lissajous", LissajousFamily),
        ("phase_space_embedding", PhaseSpaceEmbeddingFamily),
        ("dynamical_system", DynamicalSystemFamily),
        ("symbolic_regression", SymbolicRegressionFamily),
    ],
)
def test_build_family_constructs_stateless_family(name: str, family_type: type) -> None:
    assert isinstance(build_family(name, BackendSettings()), family_type)


def test_build_family_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown transform family"):
        build_family("unknown")
