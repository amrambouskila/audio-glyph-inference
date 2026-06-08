"""Tests for src/simulation/transforms/dynamical_system.py."""

from __future__ import annotations

import math

import numpy as np
import pytest
from src.simulation.transforms.dynamical_system import (
    _DUFFING,
    _RESONATOR,
    _SYSTEMS,
    _VANDERPOL,
    DynamicalSystemFamily,
    _acceleration,
    _drive_signal,
    _integrate_system,
    _system_code,
)
from src.simulation.transforms.parameter_spec import ParameterSpec

FRAME = 512
HOP = 128
N_POINTS = 256
SR = 16_000


def _frames(signal: np.ndarray) -> np.ndarray:
    count = 1 + (len(signal) - FRAME) // HOP
    return np.stack([signal[index * HOP : index * HOP + FRAME] for index in range(count)]).astype(np.float64)


def _theta(system: str = "resonator") -> dict[str, float | int | list[float] | str]:
    return {
        "system": system,
        "damping": 0.1,
        "stiffness": 1.0,
        "nonlinearity": 0.2,
        "drive_gain": 0.5,
        "initial_x": 0.4,
        "initial_v": -0.2,
        "time_scale": 1.0,
    }


def test_name_is_dynamical_system() -> None:
    assert DynamicalSystemFamily().name() == "dynamical_system"


def test_parameter_space_declares_all_forward_theta_keys() -> None:
    space = DynamicalSystemFamily().parameter_space()
    assert set(space) == set(_theta())
    assert space["system"] == ParameterSpec(kind="categorical", choices=list(_SYSTEMS))
    assert space["stiffness"] == ParameterSpec(kind="continuous", low=0.1, high=4.0)
    assert space["time_scale"].low == 0.25
    assert space["time_scale"].high == 2.0


@pytest.mark.parametrize(
    ("name", "code"),
    [("vanderpol", _VANDERPOL), ("duffing", _DUFFING), ("resonator", _RESONATOR)],
)
def test_system_code_maps_known_names(name: str, code: int) -> None:
    assert _system_code(name) == code


def test_system_code_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown dynamical system"):
        _system_code("lorenz")


def test_acceleration_vanderpol_closed_form() -> None:
    actual = _acceleration(_VANDERPOL, 2.0, 3.0, 5.0, 0.7, 1.1, 0.2, 0.4)
    expected = 0.4 * 5.0 + 0.7 * (1.0 - 0.2 * 2.0 * 2.0) * 3.0 - 1.1 * 2.0
    np.testing.assert_allclose(actual, expected, atol=1e-12)


def test_acceleration_duffing_closed_form() -> None:
    actual = _acceleration(_DUFFING, 2.0, 3.0, 5.0, 0.7, 1.1, 0.2, 0.4)
    expected = 0.4 * 5.0 - 0.7 * 3.0 - 1.1 * 2.0 - 0.2 * 2.0**3
    np.testing.assert_allclose(actual, expected, atol=1e-12)


def test_acceleration_resonator_closed_form() -> None:
    actual = _acceleration(_RESONATOR, 2.0, 3.0, 5.0, 0.7, 1.1, 0.2, 0.4)
    expected = 0.4 * 5.0 - 0.7 * 3.0 - 1.1 * 2.0
    np.testing.assert_allclose(actual, expected, atol=1e-12)


def test_integrate_system_single_sample_returns_initial_state() -> None:
    states = _integrate_system(_RESONATOR, np.zeros(1), 0.0, 1.0, 0.0, 0.0, 0.25, -0.75, 1.0)
    np.testing.assert_allclose(states, [[0.25, -0.75]], atol=1e-12)


def test_integrate_system_matches_harmonic_oscillator_reference() -> None:
    n = 2049
    drive = np.zeros(n, dtype=np.float64)
    states = _integrate_system(_RESONATOR, drive, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 2.0 * math.pi)
    t = np.linspace(0.0, 2.0 * math.pi, n)
    np.testing.assert_allclose(states[:, 0], np.cos(t), atol=5e-10)
    np.testing.assert_allclose(states[:, 1], -np.sin(t), atol=5e-10)


def test_drive_signal_resamples_and_standardizes() -> None:
    signal = np.sin(2.0 * np.pi * 440.0 * np.arange(SR) / SR)
    drive = _drive_signal(_frames(signal), N_POINTS)
    assert drive.shape == (N_POINTS,)
    np.testing.assert_allclose(drive.mean(), 0.0, atol=1e-2)
    assert drive.std() > 0.5


def test_forward_shape_dtype_range_and_determinism() -> None:
    frames = _frames(0.5 * np.sin(2.0 * np.pi * 220.0 * np.arange(SR) / SR))
    family = DynamicalSystemFamily()
    first = family.forward(frames, _theta("vanderpol"))
    second = family.forward(frames, _theta("vanderpol"))
    assert first.shape == (N_POINTS, 2)
    assert first.dtype == np.float64
    assert np.all(first >= -0.5 - 1e-9)
    assert np.all(first <= 0.5 + 1e-9)
    np.testing.assert_array_equal(first, second)


def test_forward_zero_state_zero_drive_collapses_without_error() -> None:
    theta = dict(_theta("duffing"), drive_gain=0.0, initial_x=0.0, initial_v=0.0)
    contour = DynamicalSystemFamily().forward(np.zeros((10, FRAME)), theta)
    assert contour.shape == (N_POINTS, 2)
    assert np.all(np.isfinite(contour))
    np.testing.assert_allclose(contour, 0.0, atol=1e-12)


def test_complexity_closed_form() -> None:
    theta = _theta()
    numeric = np.array([0.1, 1.0, 0.2, 0.5, 0.4, -0.2, 1.0])
    expected = len(theta) + np.log2(1.0 + np.abs(numeric)).sum()
    np.testing.assert_allclose(DynamicalSystemFamily().complexity(theta), expected, atol=1e-12)
