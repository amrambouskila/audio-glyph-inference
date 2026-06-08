"""Tests for src/simulation/baseline_thresholds.py — closed-form gate calibration checks."""

from __future__ import annotations

import numpy as np
from src.simulation.baseline_thresholds import _unit_circle, evaluate_exit_gate, exit_thresholds
from src.simulation.shape_distance import procrustes_distance

N = 64


def _ellipse(num_points: int, ratio: float) -> np.ndarray:
    t = 2.0 * np.pi * np.arange(num_points) / num_points
    return np.stack([0.5 * np.cos(t), 0.5 * ratio * np.sin(t)], axis=1)


def test_unit_circle_is_inscribed_in_box() -> None:
    circle = _unit_circle(N)
    assert circle.shape == (N, 2)
    assert circle.dtype == np.float64
    np.testing.assert_allclose(np.hypot(circle[:, 0], circle[:, 1]), 0.5, atol=1e-12)
    np.testing.assert_allclose(np.abs(circle).max(), 0.5, atol=1e-12)
    np.testing.assert_allclose(circle[0], [0.5, 0.0], atol=1e-12)


def test_threshold_is_zero_when_target_is_the_circle() -> None:
    thresholds = exit_thresholds({"o": _unit_circle(N)}, N, 0.6)
    np.testing.assert_allclose(thresholds["o"], 0.0, atol=1e-12)


def test_threshold_scales_linearly_with_margin() -> None:
    ellipse = _ellipse(N, 0.4)
    wide = exit_thresholds({"e": ellipse}, N, 0.6)["e"]
    narrow = exit_thresholds({"e": ellipse}, N, 0.4)["e"]
    assert wide > 0.0
    np.testing.assert_allclose(wide / narrow, 0.6 / 0.4, atol=1e-9)


def test_threshold_equals_margin_times_circle_distance() -> None:
    ellipse = _ellipse(N, 0.4)
    threshold = exit_thresholds({"e": ellipse}, N, 0.6)["e"]
    np.testing.assert_allclose(threshold, 0.6 * procrustes_distance(_unit_circle(N), ellipse), atol=1e-12)


def test_gate_passes_when_enough_accents_clear_the_bar() -> None:
    thresholds = {letter: 0.5 for letter in "abcd"}
    distances = {
        "acc1": {letter: 0.1 for letter in "abcd"},  # 4 within -> pass
        "acc2": {"a": 0.1, "b": 9.0, "c": 9.0, "d": 9.0},  # 1 within -> fail
        "acc3": {"a": 0.1, "b": 0.1, "c": 9.0, "d": 9.0},  # 2 within -> pass
    }
    result = evaluate_exit_gate(distances, thresholds, letter_fraction=0.5, min_accents=2)
    assert result.letters_required == 2
    assert result.per_accent_pass_counts == {"acc1": 4, "acc2": 1, "acc3": 2}
    assert result.accents_passed == 2
    assert result.passed is True


def test_gate_fails_when_too_few_accents_clear_the_bar() -> None:
    thresholds = {letter: 0.5 for letter in "abcd"}
    distances = {
        "acc1": {letter: 0.1 for letter in "abcd"},
        "acc2": {"a": 0.1, "b": 9.0, "c": 9.0, "d": 9.0},
    }
    result = evaluate_exit_gate(distances, thresholds, letter_fraction=0.5, min_accents=2)
    assert result.accents_passed == 1
    assert result.passed is False


def test_letters_required_uses_ceiling() -> None:
    thresholds = {letter: 0.5 for letter in "abc"}
    distances = {"acc1": {letter: 0.1 for letter in "abc"}}
    result = evaluate_exit_gate(distances, thresholds, letter_fraction=0.5, min_accents=1)
    assert result.letters_required == 2  # ceil(0.5 * 3)
    assert result.passed is True
