"""Tests for src/models/transform_candidate.py."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.models.transform_candidate import TransformCandidate


def _valid_payload() -> dict:
    return {
        "id": uuid4(),
        "family": "fourier_series",
        "theta": {"a0": 0.1, "phi0": 0.0},
        "shared_across_letters": True,
        "interpretability_score": 0.75,
        "simplicity_score": 0.5,
        "mean_shape_distance": 0.03,
        "created_at": datetime(2026, 4, 16, tzinfo=UTC),
    }


def test_round_trip_preserves_fields() -> None:
    candidate = TransformCandidate(**_valid_payload())
    rehydrated = TransformCandidate(**candidate.model_dump())
    assert rehydrated == candidate


def test_theta_accepts_float_values() -> None:
    payload = _valid_payload()
    payload["theta"] = {"k1": 1.0, "k2": -2.5}
    candidate = TransformCandidate(**payload)
    assert candidate.theta == {"k1": 1.0, "k2": -2.5}


def test_theta_rejects_non_float_value() -> None:
    payload = _valid_payload()
    payload["theta"] = {"k1": "not-a-float"}
    with pytest.raises(ValidationError):
        TransformCandidate(**payload)


def test_missing_required_field_raises() -> None:
    payload = _valid_payload()
    del payload["family"]
    with pytest.raises(ValidationError):
        TransformCandidate(**payload)
