"""Tests for src/simulation/shape_distance.py — closed-form reference values, no mocking."""

from __future__ import annotations

import numpy as np
from src.constants import SQRT2
from src.simulation.shape_distance import chamfer_distance, frechet_distance, procrustes_distance


def _asymmetric() -> np.ndarray:
    return np.array(
        [[0.0, 0.0], [0.3, 0.1], [0.5, -0.2], [0.1, -0.4], [-0.2, 0.2]],
        dtype=np.float64,
    )


# --- Procrustes ---


def test_procrustes_identical_is_zero() -> None:
    s = _asymmetric()
    np.testing.assert_allclose(procrustes_distance(s, s), 0.0, atol=1e-12)


def test_procrustes_rotation_invariant() -> None:
    s = _asymmetric()
    angle = np.pi / 3
    rot = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    np.testing.assert_allclose(procrustes_distance(s, s @ rot.T), 0.0, atol=1e-10)


def test_procrustes_scale_and_translation_invariant() -> None:
    s = _asymmetric()
    moved = 3.0 * s + np.array([10.0, -7.0])
    np.testing.assert_allclose(procrustes_distance(s, moved), 0.0, atol=1e-10)


def test_procrustes_reflection_is_not_zero() -> None:
    s = _asymmetric()
    mirrored = s * np.array([-1.0, 1.0])  # chiral: a no-reflection fit cannot match
    assert procrustes_distance(s, mirrored) > 1e-3


def test_procrustes_degenerate_returns_penalty() -> None:
    assert procrustes_distance(np.zeros((5, 2)), _asymmetric()) == 1.0


# --- Chamfer ---


def test_chamfer_identical_is_zero() -> None:
    s = _asymmetric()
    np.testing.assert_allclose(chamfer_distance(s, s), 0.0, atol=1e-12)


def test_chamfer_single_point_known_value() -> None:
    p = np.array([[0.0, 0.0]], dtype=np.float64)
    q = np.array([[0.0, 0.3]], dtype=np.float64)
    np.testing.assert_allclose(chamfer_distance(p, q), 0.3 / SQRT2, atol=1e-12)


def test_chamfer_raw_then_normalization() -> None:
    p = np.array([[0.0, 0.0], [0.0, 0.1]], dtype=np.float64)
    q = np.array([[0.0, 0.0], [0.0, 0.2]], dtype=np.float64)
    raw = 0.05  # (mean_PQ=0.05 + mean_QP=0.05) / 2
    np.testing.assert_allclose(chamfer_distance(p, q), raw / SQRT2, atol=1e-12)


# --- Fréchet ---


def test_frechet_identical_is_zero() -> None:
    s = _asymmetric()
    np.testing.assert_allclose(frechet_distance(s, s, cyclic_shifts=len(s)), 0.0, atol=1e-12)


def test_frechet_exact_shift_search_finds_alignment() -> None:
    s = _asymmetric()
    rolled = np.roll(s, 2, axis=0)
    np.testing.assert_allclose(frechet_distance(s, rolled, cyclic_shifts=len(s)), 0.0, atol=1e-12)


def test_frechet_too_few_shifts_misses() -> None:
    s = _asymmetric()
    rolled = np.roll(s, 2, axis=0)
    assert frechet_distance(s, rolled, cyclic_shifts=1) > 1e-6


def test_frechet_known_parallel_offset() -> None:
    p = np.array([[0.0, 0.0], [0.5, 0.0]], dtype=np.float64)
    q = np.array([[0.0, 0.2], [0.5, 0.2]], dtype=np.float64)
    np.testing.assert_allclose(frechet_distance(p, q, cyclic_shifts=1), 0.2 / SQRT2, atol=1e-9)
