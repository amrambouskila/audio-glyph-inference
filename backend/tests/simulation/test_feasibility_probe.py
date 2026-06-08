"""Tests for src/simulation/feasibility_probe.py."""

from __future__ import annotations

import numpy as np
import pytest
from src.simulation.batch_synthesis import synthesize_fourier_batch
from src.simulation.feasibility_probe import FeasibilityProbe

N_POINTS = 64


def _probe(**overrides):
    params = {
        "rho_min": 0.05,
        "overfit_ratio_max": 4.0,
        "lookup_failure_margin": 0.02,
        "no_fit_tolerance": 0.0,
    }
    params.update(overrides)
    return FeasibilityProbe(**params)


def _target_family(phi: np.ndarray) -> np.ndarray:
    theta = {
        "rank_r": 1,
        "ridge_alpha": 0.0,
        "affine_u": [0.0, 0.0, 0.0, 1.0],
        "affine_v": [1.0, 0.0],
        "affine_b": [1.0, 0.0, 0.0, 0.35],
    }
    return synthesize_fourier_batch(phi, theta, N_POINTS)


def _recoverable_dataset() -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    phi = np.array(
        [
            [-0.20, 0.0],
            [-0.10, 0.0],
            [0.10, 0.0],
            [0.20, 0.0],
            [-0.15, 0.0],
            [0.15, 0.0],
            [0.25, 0.0],
            [-0.25, 0.0],
        ],
        dtype=np.float64,
    )
    letters = ["a", "a", "b", "b", "a", "b", "a", "b"]
    accents = ["train", "train", "train", "train", "held", "held", "held", "held"]
    return phi, _target_family(phi), letters, accents


def test_closed_form_probe_recovers_known_affine_fourier_map() -> None:
    phi, targets, letters, accents = _recoverable_dataset()
    result = _probe(rho_min=0.0, lookup_failure_margin=0.0).fit(
        phi,
        targets,
        letters,
        accents,
        held_out_accent="held",
        rank_r=1,
        ridge_alpha=0.0,
        fourier_k=1,
    )
    assert result.verdict == "FEASIBLE"
    np.testing.assert_allclose(result.d_probe_in, 0.0, atol=1e-10)
    np.testing.assert_allclose(result.d_probe_out, 0.0, atol=1e-10)
    assert result.delta_lookup > 0.0
    assert result.r_track > 0.0


def test_probe_flags_adversarial_per_letter_constant_lookup() -> None:
    phi = np.array(
        [[0.0], [0.0], [1.0], [1.0], [0.0], [1.0]],
        dtype=np.float64,
    )
    targets = _target_family(np.column_stack([phi[:, 0] * 0.2 - 0.1, np.zeros(phi.shape[0])]))
    letters = ["a", "a", "b", "b", "a", "b"]
    accents = ["train", "train", "train", "train", "held", "held"]
    result = _probe(rho_min=0.01).fit(
        phi,
        targets,
        letters,
        accents,
        held_out_accent="held",
        rank_r=1,
        ridge_alpha=0.0,
        fourier_k=1,
    )
    assert result.verdict == "TRIVIAL_LOOKUP"
    np.testing.assert_allclose(result.r_track, 0.0, atol=1e-12)
    np.testing.assert_allclose(result.d_probe_in, 0.0, atol=1e-10)


@pytest.mark.parametrize(
    ("metrics", "expected"),
    [
        (
            {
                "d_probe_in": 0.5,
                "d_global_in": 0.5,
                "r_track": 1.0,
                "d_probe_out": 0.1,
                "d_const_out": 0.2,
                "overfit_ratio": 1.0,
            },
            "NO_FIT",
        ),
        (
            {
                "d_probe_in": 0.1,
                "d_global_in": 0.5,
                "r_track": 0.01,
                "d_probe_out": 0.1,
                "d_const_out": 0.2,
                "overfit_ratio": 1.0,
            },
            "TRIVIAL_LOOKUP",
        ),
        (
            {
                "d_probe_in": 0.1,
                "d_global_in": 0.5,
                "r_track": 0.1,
                "d_probe_out": 0.23,
                "d_const_out": 0.2,
                "overfit_ratio": 1.0,
            },
            "TRIVIAL_LOOKUP",
        ),
        (
            {
                "d_probe_in": 0.1,
                "d_global_in": 0.5,
                "r_track": 0.1,
                "d_probe_out": 0.1,
                "d_const_out": 0.2,
                "overfit_ratio": 4.0,
            },
            "TRIVIAL_LOOKUP",
        ),
        (
            {
                "d_probe_in": 0.1,
                "d_global_in": 0.5,
                "r_track": 0.1,
                "d_probe_out": 0.1,
                "d_const_out": 0.2,
                "overfit_ratio": 3.0,
            },
            "FEASIBLE",
        ),
    ],
)
def test_verdict_boundaries(metrics, expected) -> None:
    assert _probe().classify(**metrics) == expected


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"rho_min": -0.1}, "rho_min"),
        ({"overfit_ratio_max": 0.0}, "overfit_ratio_max"),
        ({"lookup_failure_margin": -0.1}, "lookup_failure_margin"),
        ({"no_fit_tolerance": -0.1}, "no_fit_tolerance"),
    ],
)
def test_constructor_validates_thresholds(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        _probe(**kwargs)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda phi, targets, letters, accents: (phi[:, 0], targets, letters, accents, {}), "phi"),
        (lambda phi, targets, letters, accents: (phi, targets[:, :, 0], letters, accents, {}), "targets"),
        (lambda phi, targets, letters, accents: (phi[:1], targets, letters, accents, {}), "matching length"),
        (lambda phi, targets, letters, accents: (phi[:0], targets[:0], [], [], {}), "at least one"),
        (lambda phi, targets, letters, accents: (phi, targets, letters, accents, {"rank_r": 0}), "rank_r"),
        (lambda phi, targets, letters, accents: (phi, targets, letters, accents, {"ridge_alpha": -0.1}), "ridge_alpha"),
        (lambda phi, targets, letters, accents: (phi, targets, letters, accents, {"fourier_k": 0}), "fourier_k"),
    ],
)
def test_fit_validates_shapes_and_search_knobs(mutate, message) -> None:
    phi, targets, letters, accents = _recoverable_dataset()
    bad_phi, bad_targets, bad_letters, bad_accents, overrides = mutate(phi, targets, letters, accents)
    params = {"rank_r": 1, "ridge_alpha": 0.0, "fourier_k": 1}
    params.update(overrides)
    with pytest.raises(ValueError, match=message):
        _probe().fit(
            bad_phi,
            bad_targets,
            bad_letters,
            bad_accents,
            held_out_accent="held",
            **params,
        )


def test_fit_requires_held_out_and_fitted_accents() -> None:
    phi, targets, letters, accents = _recoverable_dataset()
    with pytest.raises(ValueError, match="held_out_accent"):
        _probe().fit(phi, targets, letters, accents, held_out_accent="missing", rank_r=1, ridge_alpha=0.0, fourier_k=1)
    with pytest.raises(ValueError, match="fitted accent"):
        _probe().fit(
            phi,
            targets,
            letters,
            ["held"] * len(accents),
            held_out_accent="held",
            rank_r=1,
            ridge_alpha=0.0,
            fourier_k=1,
        )


def test_fit_rejects_held_out_letter_without_train_prototype() -> None:
    phi, targets, letters, accents = _recoverable_dataset()
    letters[-1] = "missing"
    with pytest.raises(ValueError, match="lack fitted-accent prototypes"):
        _probe().fit(phi, targets, letters, accents, held_out_accent="held", rank_r=1, ridge_alpha=0.0, fourier_k=1)
