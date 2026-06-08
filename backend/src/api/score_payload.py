"""Shared validation for generated/target score payloads."""

from __future__ import annotations

from typing import TypedDict, cast

import numpy as np


class ValidatedScorePayload(TypedDict):
    """JSON/MessagePack-ready score payload without transport metadata."""

    shape_distance: float
    contours: list[list[float]]
    target_contours: list[list[float]]


def validated_score_payload(generated: np.ndarray, target: np.ndarray, distance: float) -> ValidatedScorePayload:
    """Validate finite score geometry before API serialization.

    Args:
        generated: ndarray shape (num_points, 2) dtype=float64, units=unit-square coordinates [-0.5, 0.5].
        target: ndarray shape (num_points, 2) dtype=float64, units=unit-square coordinates [-0.5, 0.5].
        distance: shape-distance scalar in metric-specific normalized units.

    Returns:
        Serialization-ready score payload with finite contour coordinates and distance.
    """
    validate_score_geometry(generated, target)
    if not np.isfinite(distance):
        raise ValueError("shape_distance must be finite")
    return {
        "shape_distance": float(distance),
        "contours": cast(list[list[float]], generated.tolist()),
        "target_contours": cast(list[list[float]], target.tolist()),
    }


def validate_score_geometry(generated: np.ndarray, target: np.ndarray) -> None:
    """Validate generated and target contour arrays before scoring.

    Args:
        generated: ndarray shape (num_points, 2) dtype=float64, units=unit-square coordinates [-0.5, 0.5].
        target: ndarray shape (num_points, 2) dtype=float64, units=unit-square coordinates [-0.5, 0.5].
    """
    if generated.ndim != 2 or generated.shape[1] != 2:
        raise ValueError("generated contour must have shape (num_points, 2)")
    if target.ndim != 2 or target.shape[1] != 2:
        raise ValueError("target contour must have shape (num_points, 2)")
    if not bool(np.all(np.isfinite(generated))):
        raise ValueError("generated contour coordinates must be finite")
    if not bool(np.all(np.isfinite(target))):
        raise ValueError("target contour coordinates must be finite")
