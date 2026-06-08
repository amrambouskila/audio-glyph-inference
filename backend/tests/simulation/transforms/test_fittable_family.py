"""Tests for src/simulation/transforms/fittable_family.py."""

from __future__ import annotations

import numpy as np
from src.simulation.transforms.fittable_family import FittableFamily
from src.simulation.transforms.fourier_series import FourierSeriesFamily
from src.simulation.transforms.lissajous import LissajousFamily
from src.simulation.transforms.phase_space_embedding import PhaseSpaceEmbeddingFamily


class _Fittable:
    def fit_theta(self, phi, targets, searched_theta, num_points):
        return dict(searched_theta)


class _ConcreteFittable(FittableFamily):
    def fit_theta(self, phi, targets, searched_theta, num_points):
        super().fit_theta(phi, targets, searched_theta, num_points)
        return dict(searched_theta)


class _NotFittable:
    def forward(self, audio, theta):
        return np.zeros((2, 2), dtype=np.float64)


def test_fittable_family_is_runtime_checkable() -> None:
    assert isinstance(_Fittable(), FittableFamily)
    assert not isinstance(_NotFittable(), FittableFamily)


def test_affine_phase_two_families_are_fittable() -> None:
    assert isinstance(FourierSeriesFamily(), FittableFamily)
    assert isinstance(LissajousFamily(), FittableFamily)
    assert not isinstance(PhaseSpaceEmbeddingFamily(), FittableFamily)


def test_protocol_method_returns_theta_mapping() -> None:
    theta = _ConcreteFittable().fit_theta(
        np.zeros((1, 2), dtype=np.float64),
        np.zeros((1, 4, 2), dtype=np.float64),
        {"rank_r": 1},
        4,
    )
    assert theta == {"rank_r": 1}
