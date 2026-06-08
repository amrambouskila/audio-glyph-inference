"""Registry for transform family construction."""

from __future__ import annotations

from src.config import BackendSettings
from src.simulation.transforms.dynamical_system import DynamicalSystemFamily
from src.simulation.transforms.fourier_series import FourierSeriesFamily
from src.simulation.transforms.lissajous import LissajousFamily
from src.simulation.transforms.phase_space_embedding import PhaseSpaceEmbeddingFamily
from src.simulation.transforms.symbolic_regression import SymbolicRegressionFamily
from src.simulation.transforms.transform_base import TransformFamily

FAMILY_REGISTRY: dict[str, type[TransformFamily]] = {
    "fourier_series": FourierSeriesFamily,
    "lissajous": LissajousFamily,
    "phase_space_embedding": PhaseSpaceEmbeddingFamily,
    "dynamical_system": DynamicalSystemFamily,
    "symbolic_regression": SymbolicRegressionFamily,
}


def build_family(name: str, settings: BackendSettings | None = None) -> TransformFamily:
    """Construct a stateless transform family by registry name."""
    try:
        family_type = FAMILY_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"unknown transform family {name!r}; expected one of {sorted(FAMILY_REGISTRY)}") from exc
    return family_type()
