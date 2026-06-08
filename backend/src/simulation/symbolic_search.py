"""PySR-backed symbolic coefficient proposal for SymbolicRegressionFamily."""

from __future__ import annotations

import importlib
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

import numpy as np

from src.config import BackendSettings, get_settings
from src.models.transform_candidate import TransformCandidate
from src.simulation.batch_features import compute_feature_matrix
from src.simulation.contour_compare import contour_compare
from src.simulation.lookup_ratio import lookup_ratio
from src.simulation.scoring import interpretability_score, simplicity_score
from src.simulation.transforms.transform_base import Theta, TransformFamily


class PySRUnavailableError(RuntimeError):
    """Raised when symbolic search is requested without the optional PySR extra."""


class SymbolicRegressor(Protocol):
    """Small PySRRegressor surface used by this project."""

    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        variable_names: Sequence[str],
    ) -> SymbolicRegressor:
        """Fit one scalar symbolic expression."""

    def sympy(self) -> object:
        """Return the chosen SymPy expression."""


SymbolicRegressorFactory = Callable[..., SymbolicRegressor]


def fit_symbolic_regression(
    family: TransformFamily,
    audio: Sequence[np.ndarray],
    targets: np.ndarray,
    letters: Sequence[str],
    accents: Sequence[str],
    *,
    distance_metric: str,
    max_evaluations: int,
    regularization_weight: float,
    shared_across_letters: bool,
    seed: int,
    settings: BackendSettings | None = None,
    regressor_factory: SymbolicRegressorFactory | None = None,
) -> list[TransformCandidate]:
    """Fit PySR expressions from audio features to Fourier coefficients."""
    if family.name() != "symbolic_regression":
        raise ValueError("symbolic-regression strategy requires SymbolicRegressionFamily")
    if not shared_across_letters:
        raise ValueError("symbolic-regression search currently supports only shared_across_letters=True")
    _validate_inputs(audio, targets, letters, accents, max_evaluations, regularization_weight)
    resolved_settings = settings or get_settings()
    factory = regressor_factory or _default_regressor_factory()
    phi = compute_feature_matrix(
        audio,
        sample_rate_hz=resolved_settings.audio_sample_rate_hz,
        n_mels=resolved_settings.feature_n_mels,
        n_segments=resolved_settings.feature_n_segments,
    )
    order = resolved_settings.symbolic_fourier_k
    coeff_targets = fit_fourier_coefficients(targets, order)
    variable_names = [f"f{index}" for index in range(phi.shape[1])]
    expressions = [
        _fit_expression(
            factory,
            phi,
            coeff_targets[:, coeff_index],
            variable_names,
            max_evaluations,
            seed + coeff_index,
            resolved_settings,
        )
        for coeff_index in range(coeff_targets.shape[1])
    ]
    theta: Theta = {"fourier_k": order}
    theta.update({f"coeff_{index}": expression for index, expression in enumerate(expressions)})
    generated = np.stack([family.forward(frames, theta) for frames in audio]).astype(np.float64)
    distances = np.asarray(
        [contour_compare(generated[index], targets[index], distance_metric) for index in range(targets.shape[0])],
        dtype=np.float64,
    )
    complexity = family.complexity(theta)
    mean_distance = float(distances.mean())
    candidate = TransformCandidate(
        id=uuid4(),
        family=family.name(),
        theta=theta,
        expression="\n".join(expressions),
        shared_across_letters=shared_across_letters,
        interpretability_score=interpretability_score(
            complexity,
            resolved_settings.interpretability_prior_symbolic,
            resolved_settings.simplicity_c_scale,
        ),
        simplicity_score=simplicity_score(complexity, resolved_settings.simplicity_c_scale),
        mean_shape_distance=mean_distance,
        lookup_ratio=lookup_ratio(generated, letters),
        created_at=datetime.now(tz=UTC),
    )
    return [candidate]


def fit_fourier_coefficients(targets: np.ndarray, order: int) -> np.ndarray:
    """Project target contours onto the real Fourier basis.

    Args:
        targets: ndarray shape (B, N, 2) dtype=float64, unit-square target contours.
        order: positive Fourier order K.

    Returns:
        ndarray shape (B, 4K) dtype=float64, least-squares Fourier coefficients.
    """
    if order <= 0:
        raise ValueError("order must be positive")
    if targets.ndim != 3 or targets.shape[2] != 2:
        raise ValueError("targets must have shape (B, N, 2)")
    basis = _fourier_basis(targets.shape[1], order)
    coeffs_x = np.linalg.lstsq(basis, targets[:, :, 0].T, rcond=None)[0].T
    coeffs_y = np.linalg.lstsq(basis, targets[:, :, 1].T, rcond=None)[0].T
    out = np.empty((targets.shape[0], 4 * order), dtype=np.float64)
    out[:, :order] = coeffs_x[:, 0::2]
    out[:, order : 2 * order] = coeffs_x[:, 1::2]
    out[:, 2 * order : 3 * order] = coeffs_y[:, 0::2]
    out[:, 3 * order :] = coeffs_y[:, 1::2]
    return out


def _fourier_basis(num_points: int, order: int) -> np.ndarray:
    t = 2.0 * np.pi * np.arange(num_points, dtype=np.float64) / num_points
    columns = []
    for harmonic in range(1, order + 1):
        columns.append(np.cos(harmonic * t))
        columns.append(np.sin(harmonic * t))
    return np.stack(columns, axis=1)


def _fit_expression(
    factory: SymbolicRegressorFactory,
    phi: np.ndarray,
    coeff_target: np.ndarray,
    variable_names: Sequence[str],
    max_evaluations: int,
    seed: int,
    settings: BackendSettings,
) -> str:
    regressor = factory(
        niterations=settings.symbolic_niterations,
        max_evals=max_evaluations,
        maxsize=settings.symbolic_maxsize,
        binary_operators=settings.symbolic_binary_operators,
        unary_operators=settings.symbolic_unary_operators,
        model_selection=settings.symbolic_model_selection,
        deterministic=True,
        parallelism="serial",
        random_state=seed,
        verbosity=0,
        progress=False,
    )
    fitted = regressor.fit(phi, coeff_target.astype(np.float64), variable_names=variable_names)
    return _expression_from_regressor(fitted)


def _expression_from_regressor(regressor: SymbolicRegressor) -> str:
    expression = regressor.sympy()
    if isinstance(expression, list):
        if len(expression) != 1:
            raise ValueError("expected one symbolic expression per coefficient")
        expression = expression[0]
    return str(expression)


def _default_regressor_factory() -> SymbolicRegressorFactory:
    return require_symbolic_regressor_factory()


def require_symbolic_regressor_factory() -> SymbolicRegressorFactory:
    """Return PySRRegressor or raise a clear optional-extra error."""
    try:
        module = importlib.import_module("pysr")
    except ImportError as exc:
        raise PySRUnavailableError("install the backend with the [symbolic] extra to run PySR search") from exc
    return module.PySRRegressor


def _validate_inputs(
    audio: Sequence[np.ndarray],
    targets: np.ndarray,
    letters: Sequence[str],
    accents: Sequence[str],
    max_evaluations: int,
    regularization_weight: float,
) -> None:
    if len(audio) == 0:
        raise ValueError("audio batch must contain at least one sample")
    if targets.ndim != 3 or targets.shape[2] != 2:
        raise ValueError("targets must have shape (B, N, 2)")
    if len(audio) != targets.shape[0] or len(letters) != targets.shape[0] or len(accents) != targets.shape[0]:
        raise ValueError("audio, targets, letters, and accents must have matching length B")
    if max_evaluations <= 0:
        raise ValueError("max_evaluations must be positive")
    if regularization_weight < 0:
        raise ValueError("regularization_weight must be non-negative")
