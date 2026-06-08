"""Dynamical-system transform family F_theta (Phase 3).

A small second-order ODE is driven by the reconstructed audio signal. The
integrated state trajectory `(x, v)` is normalized into the glyph unit square.
"""

from __future__ import annotations

import numpy as np
from numba import njit

from src.config import get_settings
from src.constants import PI
from src.simulation.contour_normalize import normalize_to_unit_square
from src.simulation.transforms.parameter_spec import ParameterSpec
from src.simulation.transforms.phase_space_embedding import _reconstruct_signal, _standardize
from src.simulation.transforms.transform_base import Theta

_SYSTEMS = ("vanderpol", "duffing", "resonator")
_VANDERPOL = 0
_DUFFING = 1
_RESONATOR = 2


def _system_code(system: str) -> int:
    """Map a system name to the integer code consumed by the JIT integrator."""
    if system == "vanderpol":
        return _VANDERPOL
    if system == "duffing":
        return _DUFFING
    if system == "resonator":
        return _RESONATOR
    raise ValueError(f"unknown dynamical system {system!r}")


@njit(cache=True)
def _acceleration(  # pragma: no cover - numba-compiled hot path is exercised but not traced.
    system_code: int,
    x: float,
    v: float,
    drive: float,
    damping: float,
    stiffness: float,
    nonlinearity: float,
    drive_gain: float,
) -> float:
    if system_code == _VANDERPOL:
        return drive_gain * drive + damping * (1.0 - nonlinearity * x * x) * v - stiffness * x
    if system_code == _DUFFING:
        return drive_gain * drive - damping * v - stiffness * x - nonlinearity * x * x * x
    return drive_gain * drive - damping * v - stiffness * x


@njit(cache=True)
def _integrate_system(  # pragma: no cover - numba-compiled hot path is exercised but not traced.
    system_code: int,
    drive: np.ndarray,
    damping: float,
    stiffness: float,
    nonlinearity: float,
    drive_gain: float,
    initial_x: float,
    initial_v: float,
    total_time: float,
) -> np.ndarray:
    """Integrate a driven second-order ODE with RK4.

    Args:
        system_code: integer system selector.
        drive: ndarray (N,) float64, standardized audio drive.
        damping: scalar damping parameter.
        stiffness: scalar linear stiffness parameter.
        nonlinearity: scalar nonlinear coefficient.
        drive_gain: scalar audio-drive gain.
        initial_x: scalar initial position.
        initial_v: scalar initial velocity.
        total_time: integration horizon in normalized seconds.

    Returns:
        ndarray (N, 2) float64, raw state trajectory columns [x, v].
    """
    n = drive.shape[0]
    states = np.empty((n, 2), dtype=np.float64)
    states[0, 0] = initial_x
    states[0, 1] = initial_v
    if n == 1:
        return states
    dt = total_time / (n - 1)
    for index in range(n - 1):
        x = states[index, 0]
        v = states[index, 1]
        u0 = drive[index]
        u1 = drive[index + 1]
        umid = 0.5 * (u0 + u1)

        k1x = v
        k1v = _acceleration(system_code, x, v, u0, damping, stiffness, nonlinearity, drive_gain)

        x2 = x + 0.5 * dt * k1x
        v2 = v + 0.5 * dt * k1v
        k2x = v2
        k2v = _acceleration(system_code, x2, v2, umid, damping, stiffness, nonlinearity, drive_gain)

        x3 = x + 0.5 * dt * k2x
        v3 = v + 0.5 * dt * k2v
        k3x = v3
        k3v = _acceleration(system_code, x3, v3, umid, damping, stiffness, nonlinearity, drive_gain)

        x4 = x + dt * k3x
        v4 = v + dt * k3v
        k4x = v4
        k4v = _acceleration(system_code, x4, v4, u1, damping, stiffness, nonlinearity, drive_gain)

        states[index + 1, 0] = x + (dt / 6.0) * (k1x + 2.0 * k2x + 2.0 * k3x + k4x)
        states[index + 1, 1] = v + (dt / 6.0) * (k1v + 2.0 * k2v + 2.0 * k3v + k4v)
    return states


def _drive_signal(audio: np.ndarray, n: int) -> np.ndarray:
    """Reconstruct and resample the audio drive.

    Args:
        audio: ndarray (num_frames, frame_length) float64, normalized amplitude [-1, 1].
        n: number of drive samples.

    Returns:
        ndarray (n,) float64, standardized audio drive.
    """
    settings = get_settings()
    signal = _standardize(_reconstruct_signal(audio, settings.audio_hop_length_samples))
    source_t = np.linspace(0.0, 1.0, signal.size)
    target_t = np.linspace(0.0, 1.0, n)
    return np.interp(target_t, source_t, signal).astype(np.float64)


class DynamicalSystemFamily:
    """F_theta where theta parameterizes an audio-driven second-order ODE."""

    def name(self) -> str:
        return "dynamical_system"

    def parameter_space(self) -> dict[str, ParameterSpec]:
        return {
            "system": ParameterSpec(kind="categorical", choices=list(_SYSTEMS)),
            "damping": ParameterSpec(kind="continuous", low=0.0, high=2.0),
            "stiffness": ParameterSpec(kind="continuous", low=0.1, high=4.0),
            "nonlinearity": ParameterSpec(kind="continuous", low=0.0, high=3.0),
            "drive_gain": ParameterSpec(kind="continuous", low=0.0, high=2.0),
            "initial_x": ParameterSpec(kind="continuous", low=-1.0, high=1.0),
            "initial_v": ParameterSpec(kind="continuous", low=-1.0, high=1.0),
            "time_scale": ParameterSpec(kind="continuous", low=0.25, high=2.0),
        }

    def complexity(self, theta: Theta) -> float:
        """Parameter count plus log-magnitude cost of active continuous terms."""
        numeric = np.array(
            [
                float(theta["damping"]),
                float(theta["stiffness"]),
                float(theta["nonlinearity"]),
                float(theta["drive_gain"]),
                float(theta["initial_x"]),
                float(theta["initial_v"]),
                float(theta["time_scale"]),
            ],
            dtype=np.float64,
        )
        return float(len(self.parameter_space()) + np.log2(1.0 + np.abs(numeric)).sum())

    def forward(self, audio: np.ndarray, theta: Theta) -> np.ndarray:
        """Map preprocessed audio frames to a dynamical-system trajectory contour.

        Args:
            audio: ndarray (num_frames, frame_length) float64, normalized amplitude [-1, 1].
            theta: system / damping / stiffness / nonlinearity / drive_gain / initial state / time_scale.

        Returns:
            ndarray (N, 2) float64 in [-0.5, 0.5], N = glyph_contour_num_points.
        """
        settings = get_settings()
        n = settings.glyph_contour_num_points
        drive = _drive_signal(audio, n)
        states = _integrate_system(
            _system_code(str(theta["system"])),
            drive,
            float(theta["damping"]),
            float(theta["stiffness"]),
            float(theta["nonlinearity"]),
            float(theta["drive_gain"]),
            float(theta["initial_x"]),
            float(theta["initial_v"]),
            2.0 * PI * float(theta["time_scale"]),
        )
        return normalize_to_unit_square(states).astype(np.float64)
