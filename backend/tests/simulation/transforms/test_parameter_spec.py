"""Tests for src/simulation/transforms/parameter_spec.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.simulation.transforms.parameter_spec import ParameterSpec


def test_continuous_round_trip() -> None:
    spec = ParameterSpec(kind="continuous", low=-1.0, high=1.0)
    assert ParameterSpec(**spec.model_dump()) == spec


def test_integer_spec_valid() -> None:
    spec = ParameterSpec(kind="integer", low=1, high=8)
    assert spec.high == 8.0


def test_categorical_spec_valid() -> None:
    spec = ParameterSpec(kind="categorical", choices=["vanderpol", "duffing"])
    assert spec.choices == ["vanderpol", "duffing"]


def test_continuous_requires_bounds() -> None:
    with pytest.raises(ValidationError):
        ParameterSpec(kind="continuous", low=0.0)


def test_continuous_high_must_exceed_low() -> None:
    with pytest.raises(ValidationError):
        ParameterSpec(kind="continuous", low=1.0, high=1.0)


def test_continuous_rejects_choices() -> None:
    with pytest.raises(ValidationError):
        ParameterSpec(kind="continuous", low=0.0, high=1.0, choices=["x"])


def test_categorical_requires_choices() -> None:
    with pytest.raises(ValidationError):
        ParameterSpec(kind="categorical")


def test_categorical_rejects_bounds() -> None:
    with pytest.raises(ValidationError):
        ParameterSpec(kind="categorical", choices=["x"], low=0.0)


def test_invalid_kind_rejected() -> None:
    with pytest.raises(ValidationError):
        ParameterSpec(kind="weird", low=0.0, high=1.0)
