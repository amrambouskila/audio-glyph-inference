"""Tests for src.api.score_payload."""

from __future__ import annotations

import numpy as np
import pytest
from src.api.score_payload import validate_score_geometry, validated_score_payload


def _contour() -> np.ndarray:
    return np.array([[0.0, 0.0], [0.5, 0.0], [0.0, 0.5]], dtype=np.float64)


def test_validated_score_payload_serializes_finite_geometry() -> None:
    contour = _contour()

    payload = validated_score_payload(contour, contour, 0.25)

    assert payload == {
        "shape_distance": 0.25,
        "contours": [[0.0, 0.0], [0.5, 0.0], [0.0, 0.5]],
        "target_contours": [[0.0, 0.0], [0.5, 0.0], [0.0, 0.5]],
    }


def test_validated_score_payload_rejects_nonfinite_distance() -> None:
    contour = _contour()

    with pytest.raises(ValueError, match="shape_distance"):
        validated_score_payload(contour, contour, np.inf)


def test_validate_score_geometry_rejects_malformed_contours() -> None:
    contour = _contour()
    bad_generated = contour.copy()
    bad_generated[0, 0] = np.nan
    bad_target = contour.copy()
    bad_target[0, 1] = np.inf

    with pytest.raises(ValueError, match="generated contour.*shape"):
        validate_score_geometry(contour[:, 0], contour)
    with pytest.raises(ValueError, match="target contour.*shape"):
        validate_score_geometry(contour, contour[:, 0])
    with pytest.raises(ValueError, match="generated contour coordinates"):
        validate_score_geometry(bad_generated, contour)
    with pytest.raises(ValueError, match="target contour coordinates"):
        validate_score_geometry(contour, bad_target)
