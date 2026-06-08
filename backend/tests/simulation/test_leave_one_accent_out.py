"""Tests for src/simulation/leave_one_accent_out.py."""

from __future__ import annotations

import numpy as np
import pytest
from src.constants import HEBREW_LETTERS
from src.simulation.leave_one_accent_out import (
    _fold_indices,
    _score_fold,
    evaluate_leave_one_accent_out,
)

from tests._fixtures.ellipse_family import EllipseFamily

FRAME = 512
N_POINTS = 256
ALEF = HEBREW_LETTERS[0]
BET = HEBREW_LETTERS[1]


def _audio_batch() -> list[np.ndarray]:
    rng = np.random.default_rng(12)
    return [rng.standard_normal((3 + index % 2, FRAME)).astype(np.float64) for index in range(4)]


def _ellipse(b: float) -> np.ndarray:
    return EllipseFamily().forward(np.zeros((3, FRAME), dtype=np.float64), {"b": b})


def _targets() -> np.ndarray:
    return np.repeat(_ellipse(0.275)[None, :, :], 4, axis=0)


def test_evaluate_leave_one_accent_out_recovers_shared_ellipse_and_gate() -> None:
    result = evaluate_leave_one_accent_out(
        EllipseFamily(),
        _audio_batch(),
        _targets(),
        [ALEF, BET, ALEF, BET],
        ["ashkenazi", "ashkenazi", "chabad", "chabad"],
        distance_metric="procrustes",
        strategy="grid",
        max_evaluations=5,
        regularization_weight=0.0,
        seed=5,
        thresholds={ALEF: 1e-9, BET: 1e-9},
        letter_fraction=1.0,
        min_accents=2,
    )
    assert result.family == "ellipse"
    assert set(result.distances_by_accent) == {"ashkenazi", "chabad"}
    assert set(result.best_candidate_id_by_accent) == {"ashkenazi", "chabad"}
    np.testing.assert_allclose(result.mean_distance_by_accent["ashkenazi"], 0.0, atol=1e-12)
    np.testing.assert_allclose(result.mean_distance_by_accent["chabad"], 0.0, atol=1e-12)
    assert result.exit_gate is not None
    assert result.exit_gate.passed is True
    assert result.exit_gate.per_accent_pass_counts == {"ashkenazi": 2, "chabad": 2}


def test_evaluate_leave_one_accent_out_without_thresholds_omits_gate() -> None:
    result = evaluate_leave_one_accent_out(
        EllipseFamily(),
        _audio_batch(),
        _targets(),
        [ALEF, BET, ALEF, BET],
        ["ashkenazi", "ashkenazi", "chabad", "chabad"],
        distance_metric="procrustes",
        strategy="grid",
        max_evaluations=5,
        regularization_weight=0.0,
        seed=5,
    )
    assert result.exit_gate is None


def test_fold_indices_split_held_out_accent() -> None:
    train, test = _fold_indices(["a", "b", "a"], "a")
    np.testing.assert_array_equal(train, [1])
    np.testing.assert_array_equal(test, [0, 2])


def test_score_fold_aggregates_repeated_letters() -> None:
    audio = _audio_batch()
    targets = _targets()
    distances = _score_fold(
        EllipseFamily(),
        {"b": 0.275},
        audio,
        targets,
        [ALEF, ALEF, BET, BET],
        np.array([0, 1, 2, 3], dtype=np.int64),
        "procrustes",
    )
    assert set(distances) == {ALEF, BET}
    np.testing.assert_allclose(distances[ALEF], 0.0, atol=1e-12)
    np.testing.assert_allclose(distances[BET], 0.0, atol=1e-12)


@pytest.mark.parametrize(
    ("audio", "targets", "letters", "accents", "match"),
    [
        ([], np.zeros((0, N_POINTS, 2), dtype=np.float64), [], [], "at least one"),
        (_audio_batch()[:1], np.zeros((1, N_POINTS), dtype=np.float64), [ALEF], ["a"], "shape"),
        (_audio_batch()[:1], _targets()[:1], [ALEF, BET], ["a"], "matching length"),
        (_audio_batch()[:2], _targets()[:2], [ALEF, BET], ["a", "a"], "at least two accents"),
    ],
)
def test_evaluate_leave_one_accent_out_validates_inputs(
    audio: list[np.ndarray],
    targets: np.ndarray,
    letters: list[str],
    accents: list[str],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        evaluate_leave_one_accent_out(
            EllipseFamily(),
            audio,
            targets,
            letters,
            accents,
            distance_metric="procrustes",
            strategy="grid",
            max_evaluations=5,
            regularization_weight=0.0,
            seed=5,
        )
