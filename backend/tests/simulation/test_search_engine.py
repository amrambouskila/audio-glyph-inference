"""Tests for src/simulation/search_engine.py."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
import pytest
from src.config import BackendSettings
from src.constants import MULTI_STROKE_LETTERS
from src.models.transform_candidate import TransformCandidate
from src.simulation.batch_features import compute_feature_matrix
from src.simulation.lookup_ratio import align_to_reference, lookup_ratio
from src.simulation.search_engine import SearchEngine
from src.simulation.transforms.fourier_series import FourierSeriesFamily
from src.simulation.transforms.lissajous import LissajousFamily
from src.simulation.transforms.parameter_spec import ParameterSpec
from src.simulation.transforms.phase_space_embedding import PhaseSpaceEmbeddingFamily
from src.simulation.transforms.symbolic_regression import SymbolicRegressionFamily

from tests._fixtures.ellipse_family import EllipseFamily

SR = 16_000
FRAME = 512
N_MELS = 8
N_SEGMENTS = 3
N_POINTS = 256


class _MixedFamily:
    def name(self) -> str:
        return "mixed"

    def parameter_space(self) -> dict[str, ParameterSpec]:
        return {
            "mode": ParameterSpec(kind="categorical", choices=["a", "b"]),
            "steps": ParameterSpec(kind="integer", low=1, high=3),
            "x": ParameterSpec(kind="continuous", low=1.0, high=10.0),
        }

    def complexity(self, theta) -> float:
        return 0.0

    def forward(self, audio, theta):
        return np.zeros((N_POINTS, 2), dtype=np.float64)


class _NoParameterFamily:
    def name(self) -> str:
        return "no_parameter"

    def parameter_space(self) -> dict[str, ParameterSpec]:
        return {}

    def complexity(self, theta) -> float:
        return 0.0

    def forward(self, audio, theta):
        return _ellipse_targets(0.275, size=1)[0]


def _audio_batch(size: int = 6) -> list[np.ndarray]:
    rng = np.random.default_rng(4)
    frame_counts = [3, 5, 8, 3, 11, 4][:size]
    return [rng.standard_normal((num_frames, FRAME)).astype(np.float64) for num_frames in frame_counts]


def _ellipse_targets(b: float, size: int = 6) -> np.ndarray:
    family = EllipseFamily()
    target = family.forward(np.zeros((3, FRAME), dtype=np.float64), {"b": b})
    return np.repeat(target[None, :, :], size, axis=0)


def _letters(size: int = 6) -> list[str]:
    return ["א", "ב", "ג", "ד", "ו", "ז"][:size]


def test_constructor_validates_strategy_metric_and_budget() -> None:
    SearchEngine(EllipseFamily(), "procrustes", "grid", 5, 0.0)
    SearchEngine(EllipseFamily(), "procrustes", "bayesian", 5, 0.0)
    SearchEngine(SymbolicRegressionFamily(), "procrustes", "symbolic-regression", 5, 0.0)
    with pytest.raises(ValueError, match="SymbolicRegressionFamily"):
        SearchEngine(EllipseFamily(), "procrustes", "symbolic-regression", 5, 0.0)
    with pytest.raises(ValueError, match="unknown search strategy"):
        SearchEngine(EllipseFamily(), "procrustes", "bad", 5, 0.0)
    with pytest.raises(ValueError, match="unknown distance metric"):
        SearchEngine(EllipseFamily(), "bad", "grid", 5, 0.0)
    with pytest.raises(ValueError, match="positive"):
        SearchEngine(EllipseFamily(), "procrustes", "grid", 0, 0.0)
    with pytest.raises(ValueError, match="non-negative"):
        SearchEngine(EllipseFamily(), "procrustes", "grid", 5, -0.1)


def test_symbolic_strategy_dispatches_to_symbolic_search(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = TransformCandidate(
        id=uuid4(),
        family="symbolic_regression",
        theta={"fourier_k": 1, "coeff_0": "0", "coeff_1": "0", "coeff_2": "0", "coeff_3": "0"},
        expression="0",
        shared_across_letters=True,
        interpretability_score=0.5,
        simplicity_score=0.5,
        mean_shape_distance=0.0,
        lookup_ratio=0.0,
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )

    def fake_fit_symbolic_regression(*args, **kwargs):
        assert kwargs["distance_metric"] == "procrustes"
        return [expected]

    monkeypatch.setattr("src.simulation.search_engine.fit_symbolic_regression", fake_fit_symbolic_regression)

    engine = SearchEngine(SymbolicRegressionFamily(), "procrustes", "symbolic-regression", 5, 0.0)
    candidates = engine.fit(
        _audio_batch(1),
        _ellipse_targets(0.2, 1),
        ["×"],
        ["ashkenazi"],
        shared_across_letters=True,
        seed=3,
    )
    assert candidates == [expected]


def test_decode_handles_continuous_integer_categorical_and_shape_errors() -> None:
    engine = SearchEngine(_MixedFamily(), "procrustes", "grid", 12, 0.0)
    theta = engine._decode(np.array([0.9, 0.9, 0.5], dtype=np.float64))
    assert theta == {"mode": "b", "steps": 3, "x": 5.5}
    clipped = engine._decode(np.array([-1.0, 2.0, 1.0], dtype=np.float64))
    assert clipped == {"mode": "a", "steps": 3, "x": 10.0}
    with pytest.raises(ValueError, match="shape"):
        engine._decode(np.array([0.5], dtype=np.float64))


def test_decode_log_scale_key_uses_logarithmic_spacing() -> None:
    engine = SearchEngine(FourierSeriesFamily(), "procrustes", "grid", 45, 0.0)
    theta = engine._decode(np.array([0.5, 0.5], dtype=np.float64))
    np.testing.assert_allclose(theta["ridge_alpha"], 0.01, atol=1e-12)
    assert theta["rank_r"] == 2


def test_decode_and_grid_axis_defensive_spec_guards() -> None:
    engine = SearchEngine(_MixedFamily(), "procrustes", "grid", 12, 0.0)
    settings = BackendSettings(search_log_scale_keys=frozenset({"bad"}))
    bad_continuous = ParameterSpec.model_construct(kind="continuous", low=None, high=1.0, choices=None)
    bad_log = ParameterSpec.model_construct(kind="continuous", low=0.0, high=1.0, choices=None)
    bad_integer = ParameterSpec.model_construct(kind="integer", low=None, high=3.0, choices=None)
    bad_categorical = ParameterSpec.model_construct(kind="categorical", low=None, high=None, choices=None)
    with pytest.raises(ValueError, match="positive bounds"):
        engine._decode_value("bad", bad_log, 0.5, settings)
    with pytest.raises(ValueError, match="continuous"):
        engine._decode_value("x", bad_continuous, 0.5, BackendSettings())
    with pytest.raises(ValueError, match="integer"):
        engine._decode_value("steps", bad_integer, 0.5, BackendSettings())
    with pytest.raises(ValueError, match="categorical"):
        engine._decode_value("mode", bad_categorical, 0.5, BackendSettings())
    with pytest.raises(ValueError, match="integer"):
        engine._grid_axis(bad_integer, 5)
    with pytest.raises(ValueError, match="categorical"):
        engine._grid_axis(bad_categorical, 5)
    np.testing.assert_allclose(
        engine._grid_axis(ParameterSpec(kind="categorical", choices=["a", "b"]), 5),
        [0.25, 0.75],
        atol=1e-12,
    )


def test_grid_thetas_fail_loud_or_seeded_shuffle(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SearchEngine(EllipseFamily(), "procrustes", "grid", 3, 0.0)
    with pytest.raises(ValueError, match="exceeding"):
        engine._grid_thetas(seed=0, settings=BackendSettings())
    monkeypatch.setenv("BACKEND_SEARCH_GRID_TRUNCATION", "seeded-shuffle")
    shuffled = engine._grid_thetas(seed=7, settings=BackendSettings())
    repeated = engine._grid_thetas(seed=7, settings=BackendSettings())
    assert shuffled == repeated
    assert len(shuffled) == 3


def test_grid_recovers_on_lattice_ellipse_parameter() -> None:
    audio = _audio_batch()
    targets = _ellipse_targets(0.275)
    engine = SearchEngine(EllipseFamily(), "procrustes", "grid", 5, 0.0)
    candidates = engine.fit(audio, targets, _letters(), ["ashkenazi"] * len(audio), shared_across_letters=True, seed=0)
    assert len(candidates) == 5
    assert candidates[0].family == "ellipse"
    np.testing.assert_allclose(candidates[0].theta["b"], 0.275, atol=1e-12)
    np.testing.assert_allclose(candidates[0].mean_shape_distance, 0.0, atol=1e-12)
    assert candidates[0].lookup_ratio >= 0.0


def test_cma_recovers_ellipse_parameter() -> None:
    audio = _audio_batch()
    targets = _ellipse_targets(0.275)
    engine = SearchEngine(EllipseFamily(), "procrustes", "cma-es", 40, 0.0)
    candidates = engine.fit(audio, targets, _letters(), ["ashkenazi"] * len(audio), shared_across_letters=True, seed=2)
    np.testing.assert_allclose(candidates[0].theta["b"], 0.275, atol=1e-2)


def test_bayesian_recovers_ellipse_parameter() -> None:
    audio = _audio_batch()
    targets = _ellipse_targets(0.275)
    engine = SearchEngine(EllipseFamily(), "procrustes", "bayesian", 24, 0.0)
    candidates = engine.fit(audio, targets, _letters(), ["ashkenazi"] * len(audio), shared_across_letters=True, seed=2)
    repeated = engine.fit(audio, targets, _letters(), ["ashkenazi"] * len(audio), shared_across_letters=True, seed=2)
    np.testing.assert_allclose(candidates[0].theta["b"], 0.275, atol=3e-2)
    assert candidates[0].theta == repeated[0].theta


def test_bayesian_expected_improvement_favors_better_candidates() -> None:
    engine = SearchEngine(EllipseFamily(), "procrustes", "bayesian", 5, 0.0)
    observed_x = np.array([[0.0], [1.0]], dtype=np.float64)
    observed_y = np.array([0.0, 1.0], dtype=np.float64)
    candidates_x = np.array([[0.05], [0.95]], dtype=np.float64)

    acquisition = engine._expected_improvement(observed_x, observed_y, candidates_x, BackendSettings())

    assert acquisition[0] > acquisition[1]


def test_bayesian_handles_zero_parameter_and_zero_variance_cases() -> None:
    audio = _audio_batch(size=1)
    targets = _ellipse_targets(0.275, size=1)
    engine = SearchEngine(_NoParameterFamily(), "procrustes", "bayesian", 3, 0.0)

    candidates = engine.fit(audio, targets, ["×"], ["ashkenazi"], shared_across_letters=True, seed=2)

    assert candidates[0].theta == {}

    acquisition = SearchEngine(EllipseFamily(), "procrustes", "bayesian", 3, 0.0)._expected_improvement(
        np.array([[0.0], [1.0]], dtype=np.float64),
        np.array([1.0, 1.0], dtype=np.float64),
        np.array([[0.25], [0.75]], dtype=np.float64),
        BackendSettings(),
    )
    assert np.isfinite(acquisition).all()


def test_cma_rejects_non_continuous_search_space() -> None:
    audio = _audio_batch()
    targets = _ellipse_targets(0.275)
    engine = SearchEngine(PhaseSpaceEmbeddingFamily(), "procrustes", "cma-es", 5, 0.0)
    with pytest.raises(ValueError, match="continuous"):
        engine.fit(audio, targets, _letters(), ["ashkenazi"] * len(audio), shared_across_letters=True, seed=0)


def test_lissajous_fit_uses_fittable_branch() -> None:
    audio = _audio_batch()
    phi = compute_feature_matrix(audio, sample_rate_hz=SR, n_mels=N_MELS, n_segments=N_SEGMENTS)
    target_theta = {
        "freq_ratio_a": 1,
        "freq_ratio_b": 1,
        "affine_w": [0.0] * (3 * phi.shape[1]),
        "affine_b": [0.0, 2.0, 1.0],
    }
    targets = np.stack([LissajousFamily().forward(frames, target_theta) for frames in audio])
    engine = SearchEngine(LissajousFamily(), "procrustes", "grid", 25, 0.0)
    candidates = engine.fit(audio, targets, _letters(), ["ashkenazi"] * len(audio), shared_across_letters=True, seed=0)
    assert {"affine_w", "affine_b"}.issubset(candidates[0].theta)
    assert candidates[0].shared_across_letters is True


def test_fourier_grid_adds_transient_k_and_removes_it_from_candidate_theta() -> None:
    audio = _audio_batch()
    targets = _ellipse_targets(0.25)
    engine = SearchEngine(FourierSeriesFamily(), "procrustes", "grid", 45, 0.0)
    candidates = engine.fit(audio, targets, _letters(), ["ashkenazi"] * len(audio), shared_across_letters=True, seed=0)
    assert "fourier_k" not in candidates[0].theta
    assert len(candidates[0].theta["affine_b"]) in {4, 8, 12}


def test_per_letter_fit_returns_non_shared_candidates() -> None:
    audio = _audio_batch(size=4)
    targets = _ellipse_targets(0.275, size=4)
    engine = SearchEngine(EllipseFamily(), "procrustes", "grid", 5, 0.0)
    candidates = engine.fit(
        audio,
        targets,
        ["ב", "א", "ב", "א"],
        ["ashkenazi"] * 4,
        shared_across_letters=False,
        seed=0,
    )
    assert candidates
    assert all(candidate.shared_across_letters is False for candidate in candidates)


def test_sharing_multiplier_penalizes_per_letter_candidates() -> None:
    engine = SearchEngine(EllipseFamily(), "procrustes", "grid", 5, 0.0)
    settings = BackendSettings(search_per_letter_penalty=0.5)
    np.testing.assert_allclose(engine._sharing_multiplier(True, settings), 1.0, atol=1e-12)
    np.testing.assert_allclose(engine._sharing_multiplier(False, settings), 12.0, atol=1e-12)


def test_family_prior_uses_phase_space_and_unknown_defaults() -> None:
    phase_engine = SearchEngine(PhaseSpaceEmbeddingFamily(), "procrustes", "grid", 5, 0.0)
    unknown_engine = SearchEngine(EllipseFamily(), "procrustes", "grid", 5, 0.0)
    settings = BackendSettings(interpretability_prior_phase_space=0.7)
    np.testing.assert_allclose(phase_engine._family_prior(settings), 0.7, atol=1e-12)
    np.testing.assert_allclose(unknown_engine._family_prior(settings), 1.0, atol=1e-12)


def test_distance_branches_and_multistroke_substitution(monkeypatch: pytest.MonkeyPatch) -> None:
    generated = _ellipse_targets(0.2, size=2)
    targets = _ellipse_targets(0.3, size=2)
    letters = ["א", next(iter(MULTI_STROKE_LETTERS))]
    engine = SearchEngine(EllipseFamily(), "procrustes", "grid", 5, 0.0)
    distances = engine._distances(generated, targets, letters, BackendSettings())
    chamfer_engine = SearchEngine(EllipseFamily(), "chamfer", "grid", 5, 0.0)
    chamfer = chamfer_engine._distances(generated, targets, letters, BackendSettings())
    np.testing.assert_allclose(distances[1], chamfer[1], atol=1e-12)

    frechet_engine = SearchEngine(EllipseFamily(), "frechet", "grid", 5, 0.0)
    frechet = frechet_engine._distances(generated[:1], targets[:1], ["א"], BackendSettings())
    assert frechet.shape == (1,)

    monkeypatch.setenv("BACKEND_SEARCH_MULTISTROKE_METRIC", "error")
    with pytest.raises(ValueError, match="multi-stroke"):
        engine._distances(generated, targets, letters, BackendSettings())


def test_lookup_ratio_fires_on_per_letter_constant_shapes() -> None:
    alef = _ellipse_targets(0.2, size=1)[0]
    bet = _ellipse_targets(0.4, size=1)[0]
    generated = np.stack([alef, alef, bet, bet])
    ratio = lookup_ratio(generated, ["א", "א", "ב", "ב"])
    np.testing.assert_allclose(ratio, 0.0, atol=1e-12)
    assert np.isinf(lookup_ratio(np.stack([alef, alef]), ["א", "א"]))


def test_align_to_reference_handles_degenerate_and_rotated_contours() -> None:
    target = _ellipse_targets(0.3, size=1)[0]
    rotated = target @ np.array([[0.0, -1.0], [1.0, 0.0]])
    reflected = target * np.array([-1.0, 1.0])
    aligned = align_to_reference(rotated, target)
    assert aligned.shape == target.shape
    assert np.isfinite(aligned).all()
    assert np.isfinite(align_to_reference(reflected, target)).all()
    np.testing.assert_allclose(align_to_reference(np.zeros_like(target), target), 0.0, atol=1e-12)


def test_fit_input_validation() -> None:
    engine = SearchEngine(EllipseFamily(), "procrustes", "grid", 5, 0.0)
    audio = _audio_batch(size=1)
    targets = _ellipse_targets(0.275, size=1)
    with pytest.raises(ValueError, match="at least one"):
        engine.fit([], targets[:0], [], [], shared_across_letters=True, seed=0)
    with pytest.raises(ValueError, match="shape"):
        engine.fit(
            audio,
            np.zeros((1, N_POINTS), dtype=np.float64),
            ["א"],
            ["ashkenazi"],
            shared_across_letters=True,
            seed=0,
        )
    with pytest.raises(ValueError, match="matching length"):
        engine.fit(audio, targets, ["א", "ב"], ["ashkenazi"], shared_across_letters=True, seed=0)
