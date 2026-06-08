"""Leave-one-accent-out evaluation harness for Phase 3."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import numpy as np

from src.models.leave_one_accent_out_result import LeaveOneAccentOutResult
from src.simulation.baseline_thresholds import evaluate_exit_gate
from src.simulation.contour_compare import contour_compare
from src.simulation.search_engine import SearchEngine
from src.simulation.transforms.transform_base import TransformFamily


def evaluate_leave_one_accent_out(
    family: TransformFamily,
    audio: Sequence[np.ndarray],
    targets: np.ndarray,
    letters: Sequence[str],
    accents: Sequence[str],
    *,
    distance_metric: str,
    strategy: str,
    max_evaluations: int,
    regularization_weight: float,
    seed: int,
    thresholds: dict[str, float] | None = None,
    letter_fraction: float = 0.5,
    min_accents: int = 2,
) -> LeaveOneAccentOutResult:
    """Fit one shared candidate per held-out accent and score the held-out fold.

    Args:
        family: stateless TransformFamily under evaluation.
        audio: sequence length B of ndarrays (num_frames_i, frame_length) dtype=float64, normalized amplitude.
        targets: ndarray shape (B, N, 2) dtype=float64, target contours in unit-square coordinates.
        letters: length-B letter labels.
        accents: length-B accent labels.
        distance_metric: procrustes / frechet / chamfer.
        strategy: SearchEngine strategy for each training fold.
        max_evaluations: per-fold search budget.
        regularization_weight: lambda weight for Complexity(F_theta).
        seed: base RNG seed; fold index is added deterministically.
        thresholds: optional letter -> exit threshold for a gate verdict.
        letter_fraction: fraction of letters that must clear threshold per accent.
        min_accents: number of held-out accents required to clear the gate.
    """
    _validate_inputs(audio, targets, letters, accents)
    distances_by_accent: dict[str, dict[str, float]] = {}
    mean_distance_by_accent: dict[str, float] = {}
    best_candidate_id_by_accent: dict[str, UUID] = {}
    for fold_index, held_out_accent in enumerate(sorted(set(accents))):
        train_indices, test_indices = _fold_indices(accents, held_out_accent)
        engine = SearchEngine(
            family,
            distance_metric,
            strategy,
            max_evaluations,
            regularization_weight,
        )
        candidates = engine.fit(
            [audio[int(index)] for index in train_indices],
            targets[train_indices],
            [letters[int(index)] for index in train_indices],
            [accents[int(index)] for index in train_indices],
            shared_across_letters=True,
            seed=seed + fold_index,
        )
        best = candidates[0]
        fold_distances = _score_fold(family, best.theta, audio, targets, letters, test_indices, distance_metric)
        distances_by_accent[held_out_accent] = fold_distances
        mean_distance_by_accent[held_out_accent] = float(np.mean(list(fold_distances.values())))
        best_candidate_id_by_accent[held_out_accent] = best.id
    exit_gate = (
        evaluate_exit_gate(
            distances_by_accent,
            thresholds,
            letter_fraction=letter_fraction,
            min_accents=min_accents,
        )
        if thresholds is not None
        else None
    )
    return LeaveOneAccentOutResult(
        family=family.name(),
        search_strategy=strategy,
        scoring_metric=distance_metric,
        distances_by_accent=distances_by_accent,
        mean_distance_by_accent=mean_distance_by_accent,
        best_candidate_id_by_accent=best_candidate_id_by_accent,
        exit_gate=exit_gate,
    )


def _validate_inputs(
    audio: Sequence[np.ndarray],
    targets: np.ndarray,
    letters: Sequence[str],
    accents: Sequence[str],
) -> None:
    if len(audio) == 0:
        raise ValueError("audio batch must contain at least one sample")
    if targets.ndim != 3 or targets.shape[2] != 2:
        raise ValueError("targets must have shape (B, N, 2)")
    if len(audio) != targets.shape[0] or len(letters) != targets.shape[0] or len(accents) != targets.shape[0]:
        raise ValueError("audio, targets, letters, and accents must have matching length B")
    if len(set(accents)) < 2:
        raise ValueError("leave-one-accent-out evaluation requires at least two accents")


def _fold_indices(accents: Sequence[str], held_out_accent: str) -> tuple[np.ndarray, np.ndarray]:
    test = np.asarray([accent == held_out_accent for accent in accents], dtype=bool)
    indices = np.arange(len(accents), dtype=np.int64)
    return indices[~test], indices[test]


def _score_fold(
    family: TransformFamily,
    theta: dict[str, float | int | list[float] | str],
    audio: Sequence[np.ndarray],
    targets: np.ndarray,
    letters: Sequence[str],
    test_indices: np.ndarray,
    distance_metric: str,
) -> dict[str, float]:
    per_letter: dict[str, list[float]] = {}
    for index in test_indices:
        generated = family.forward(audio[int(index)], theta)
        distance = contour_compare(generated, targets[int(index)], distance_metric)
        per_letter.setdefault(letters[int(index)], []).append(distance)
    return {letter: float(np.mean(values)) for letter, values in sorted(per_letter.items())}
