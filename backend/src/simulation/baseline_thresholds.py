"""Exit-gate baseline calibration (docs/phases/phase-2-plan.md §6/§9).

Computes the per-letter "beat the trivial circle" threshold and aggregates a
leave-one-accent-out distance table into a GO/NO-GO verdict. The unit circle is
a non-trivial null (a real shape carrying zero audio information): a candidate
must beat `baseline_margin · d_circle(letter)` to count as having learned the
glyph rather than a generic blob. Pure; calibration constants are passed in by
the caller from config.
"""

from __future__ import annotations

import math

import numpy as np

from src.models.exit_gate_result import ExitGateResult
from src.simulation.contour_compare import contour_compare


def _unit_circle(num_points: int) -> np.ndarray:
    """Closed unit circle inscribed in the unit square (max|coord| == 0.5). Returns (N, 2) float64."""
    t = 2.0 * np.pi * np.arange(num_points) / num_points
    return 0.5 * np.stack([np.cos(t), np.sin(t)], axis=1)


def exit_thresholds(
    targets: dict[str, np.ndarray],
    num_points: int,
    baseline_margin: float,
    metric: str = "procrustes",
) -> dict[str, float]:
    """Per-letter exit threshold = baseline_margin · distance(unit_circle, target).

    Args:
        targets: letter -> ndarray (num_points, 2) float64 flattened target contour in the unit square.
        num_points: contour resolution; the unit-circle baseline is built at this size to match targets.
        baseline_margin: fraction of the circle distance a candidate must beat (e.g. 0.6).
        metric: shape-distance metric name (procrustes / frechet / chamfer).

    Returns:
        letter -> float threshold (lower-is-better distance scale).
    """
    circle = _unit_circle(num_points)
    return {letter: baseline_margin * contour_compare(circle, target, metric) for letter, target in targets.items()}


def evaluate_exit_gate(
    distances_by_accent: dict[str, dict[str, float]],
    thresholds: dict[str, float],
    *,
    letter_fraction: float,
    min_accents: int,
) -> ExitGateResult:
    """Aggregate a held-out distance table against per-letter thresholds.

    Args:
        distances_by_accent: held-out accent -> (letter -> best shared-candidate distance).
        thresholds: letter -> exit threshold from exit_thresholds.
        letter_fraction: fraction of letters that must be within threshold for an accent to pass.
        min_accents: number of held-out accents that must pass for the run to clear the gate.
    """
    letters_required = math.ceil(letter_fraction * len(thresholds))
    per_accent = {
        accent: sum(1 for letter, distance in distances.items() if distance <= thresholds[letter])
        for accent, distances in distances_by_accent.items()
    }
    accents_passed = sum(1 for count in per_accent.values() if count >= letters_required)
    return ExitGateResult(
        passed=accents_passed >= min_accents,
        accents_passed=accents_passed,
        letters_required=letters_required,
        per_accent_pass_counts=per_accent,
    )
