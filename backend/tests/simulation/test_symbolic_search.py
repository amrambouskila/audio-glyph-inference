"""Tests for src/simulation/symbolic_search.py."""

from __future__ import annotations

import importlib
import types
from collections.abc import Sequence

import numpy as np
import pytest
from src.config import BackendSettings
from src.simulation.symbolic_search import (
    PySRUnavailableError,
    _default_regressor_factory,
    _expression_from_regressor,
    _fit_expression,
    _fourier_basis,
    fit_fourier_coefficients,
    fit_symbolic_regression,
    require_symbolic_regressor_factory,
)
from src.simulation.transforms.fourier_series import _synthesize
from src.simulation.transforms.symbolic_regression import SymbolicRegressionFamily

FRAME = 512
N_POINTS = 256


class _ConstantRegressor:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.expression = "0.0"

    def fit(self, x: np.ndarray, y: np.ndarray, *, variable_names: Sequence[str]) -> _ConstantRegressor:
        assert x.ndim == 2
        assert variable_names[0] == "f0"
        self.expression = f"{float(np.mean(y)):.12g}"
        return self

    def sympy(self) -> object:
        return self.expression


class _ListRegressor:
    def __init__(self, expressions: list[str]) -> None:
        self.expressions = expressions

    def sympy(self) -> object:
        return self.expressions


class _WrongFamily:
    def name(self) -> str:
        return "fourier_series"

    def parameter_space(self) -> dict[str, object]:
        return {}

    def complexity(self, theta: dict[str, object]) -> float:
        return 0.0

    def forward(self, audio: np.ndarray, theta: dict[str, object]) -> np.ndarray:
        return np.zeros((N_POINTS, 2), dtype=np.float64)


def _audio_batch(size: int = 3) -> list[np.ndarray]:
    rng = np.random.default_rng(11)
    return [rng.standard_normal((4 + index, FRAME)).astype(np.float64) for index in range(size)]


def test_fit_fourier_coefficients_recovers_known_synthesis_coefficients() -> None:
    coeffs = np.array([0.4, 0.0, 0.0, 0.2, 0.1, -0.05, 0.03, 0.02], dtype=np.float64)
    target = _synthesize(coeffs, N_POINTS)
    recovered = fit_fourier_coefficients(target[None, :, :], order=2)

    np.testing.assert_allclose(recovered[0], coeffs, atol=1e-12)


def test_fit_fourier_coefficients_validates_order_and_shape() -> None:
    with pytest.raises(ValueError, match="positive"):
        fit_fourier_coefficients(np.zeros((1, N_POINTS, 2), dtype=np.float64), order=0)
    with pytest.raises(ValueError, match="shape"):
        fit_fourier_coefficients(np.zeros((1, N_POINTS), dtype=np.float64), order=1)


def test_fit_symbolic_regression_builds_candidate_from_fake_external_regressor() -> None:
    audio = _audio_batch()
    coeffs = np.array([0.4, 0.0, 0.0, 0.2], dtype=np.float64)
    target = _synthesize(coeffs, N_POINTS)
    targets = np.repeat(target[None, :, :], len(audio), axis=0)
    settings = BackendSettings(symbolic_fourier_k=1, symbolic_niterations=3, symbolic_maxsize=8)

    candidates = fit_symbolic_regression(
        SymbolicRegressionFamily(),
        audio,
        targets,
        ["alef", "bet", "gimel"],
        ["ashkenazi", "chabad", "sephardi"],
        distance_metric="procrustes",
        max_evaluations=17,
        regularization_weight=0.01,
        shared_across_letters=True,
        seed=5,
        settings=settings,
        regressor_factory=_ConstantRegressor,
    )

    candidate = candidates[0]
    assert candidate.family == "symbolic_regression"
    assert candidate.shared_across_letters is True
    assert candidate.expression is not None
    assert set(candidate.theta) == {"fourier_k", "coeff_0", "coeff_1", "coeff_2", "coeff_3"}
    np.testing.assert_allclose(candidate.mean_shape_distance, 0.0, atol=1e-12)


@pytest.mark.parametrize(
    ("audio", "targets", "letters", "accents", "max_evaluations", "regularization_weight", "match"),
    [
        ([], np.zeros((0, N_POINTS, 2), dtype=np.float64), [], [], 1, 0.0, "at least one"),
        (_audio_batch(1), np.zeros((1, N_POINTS), dtype=np.float64), ["alef"], ["a"], 1, 0.0, "shape"),
        (_audio_batch(1), np.zeros((1, N_POINTS, 2), dtype=np.float64), ["alef", "bet"], ["a"], 1, 0.0, "matching"),
        (_audio_batch(1), np.zeros((1, N_POINTS, 2), dtype=np.float64), ["alef"], ["a"], 0, 0.0, "positive"),
        (_audio_batch(1), np.zeros((1, N_POINTS, 2), dtype=np.float64), ["alef"], ["a"], 1, -0.1, "non-negative"),
    ],
)
def test_fit_symbolic_regression_validates_inputs(
    audio: list[np.ndarray],
    targets: np.ndarray,
    letters: list[str],
    accents: list[str],
    max_evaluations: int,
    regularization_weight: float,
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        fit_symbolic_regression(
            SymbolicRegressionFamily(),
            audio,
            targets,
            letters,
            accents,
            distance_metric="procrustes",
            max_evaluations=max_evaluations,
            regularization_weight=regularization_weight,
            shared_across_letters=True,
            seed=1,
            settings=BackendSettings(symbolic_fourier_k=1),
            regressor_factory=_ConstantRegressor,
        )


def test_fit_symbolic_regression_rejects_wrong_family() -> None:
    with pytest.raises(ValueError, match="SymbolicRegressionFamily"):
        fit_symbolic_regression(
            _WrongFamily(),
            _audio_batch(1),
            np.zeros((1, N_POINTS, 2), dtype=np.float64),
            ["alef"],
            ["ashkenazi"],
            distance_metric="procrustes",
            max_evaluations=1,
            regularization_weight=0.0,
            shared_across_letters=True,
            seed=1,
            settings=BackendSettings(symbolic_fourier_k=1),
            regressor_factory=_ConstantRegressor,
        )


def test_fit_symbolic_regression_rejects_per_letter_symbolic_search() -> None:
    with pytest.raises(ValueError, match="shared_across_letters=True"):
        fit_symbolic_regression(
            SymbolicRegressionFamily(),
            _audio_batch(1),
            np.zeros((1, N_POINTS, 2), dtype=np.float64),
            ["alef"],
            ["ashkenazi"],
            distance_metric="procrustes",
            max_evaluations=1,
            regularization_weight=0.0,
            shared_across_letters=False,
            seed=1,
            settings=BackendSettings(symbolic_fourier_k=1),
            regressor_factory=_ConstantRegressor,
        )


def test_expression_from_regressor_accepts_scalar_or_singleton_list() -> None:
    assert _expression_from_regressor(_ListRegressor(["f0 + 1"])) == "f0 + 1"
    assert _expression_from_regressor(_ConstantRegressor()) == "0.0"
    with pytest.raises(ValueError, match="one symbolic expression"):
        _expression_from_regressor(_ListRegressor(["f0", "f1"]))


def test_fit_expression_passes_deterministic_pysr_settings() -> None:
    phi = np.ones((2, 3), dtype=np.float64)
    expression = _fit_expression(
        _ConstantRegressor,
        phi,
        np.array([1.0, 3.0], dtype=np.float64),
        ["f0", "f1", "f2"],
        max_evaluations=9,
        seed=4,
        settings=BackendSettings(symbolic_niterations=7, symbolic_maxsize=11),
    )

    assert expression == "2"


def test_default_regressor_factory_reports_missing_optional_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    original = importlib.import_module

    def fail_for_pysr(name: str, package: str | None = None) -> object:
        if name == "pysr":
            raise ImportError("missing")
        return original(name, package)

    monkeypatch.setattr(importlib, "import_module", fail_for_pysr)

    with pytest.raises(PySRUnavailableError, match="\\[symbolic\\]"):
        require_symbolic_regressor_factory()
    with pytest.raises(PySRUnavailableError, match="\\[symbolic\\]"):
        _default_regressor_factory()


def test_require_symbolic_regressor_factory_returns_pysr_regressor(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.SimpleNamespace(PySRRegressor=_ConstantRegressor)

    def import_module(name: str, package: str | None = None) -> object:
        assert package is None
        assert name == "pysr"
        return module

    monkeypatch.setattr(importlib, "import_module", import_module)

    assert require_symbolic_regressor_factory() is _ConstantRegressor


def test_fourier_basis_shape() -> None:
    basis = _fourier_basis(N_POINTS, 2)
    assert basis.shape == (N_POINTS, 4)
    np.testing.assert_allclose(basis[0], [1.0, 0.0, 1.0, 0.0], atol=1e-12)
