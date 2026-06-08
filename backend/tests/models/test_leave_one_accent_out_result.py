"""Tests for src/models/leave_one_accent_out_result.py."""

from __future__ import annotations

import math
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.constants import HEBREW_LETTERS
from src.models.exit_gate_result import ExitGateResult
from src.models.leave_one_accent_out_result import LeaveOneAccentOutResult


def test_leave_one_accent_out_result_round_trips_report() -> None:
    candidate_id = uuid4()
    result = LeaveOneAccentOutResult(
        family="ellipse",
        search_strategy="grid",
        scoring_metric="procrustes",
        distances_by_accent={"ashkenazi": {HEBREW_LETTERS[0]: 0.1}},
        mean_distance_by_accent={"ashkenazi": 0.1},
        best_candidate_id_by_accent={"ashkenazi": candidate_id},
        exit_gate=ExitGateResult(
            passed=True,
            accents_passed=1,
            letters_required=1,
            per_accent_pass_counts={"ashkenazi": 1},
        ),
    )
    dumped = result.model_dump()
    assert dumped["best_candidate_id_by_accent"]["ashkenazi"] == candidate_id
    assert result.exit_gate is not None
    assert result.exit_gate.passed is True


def test_leave_one_accent_out_result_allows_missing_gate() -> None:
    result = LeaveOneAccentOutResult(
        family="ellipse",
        search_strategy="grid",
        scoring_metric="procrustes",
        distances_by_accent={},
        mean_distance_by_accent={},
        best_candidate_id_by_accent={},
        exit_gate=None,
    )
    assert result.exit_gate is None


def test_leave_one_accent_out_result_rejects_invalid_result_maps() -> None:
    candidate_id = uuid4()
    with pytest.raises(ValidationError, match="matching keys"):
        LeaveOneAccentOutResult(
            family="ellipse",
            search_strategy="grid",
            scoring_metric="procrustes",
            distances_by_accent={"ashkenazi": {HEBREW_LETTERS[0]: 0.1}},
            mean_distance_by_accent={},
            best_candidate_id_by_accent={"ashkenazi": candidate_id},
            exit_gate=None,
        )
    with pytest.raises(ValidationError, match="constants.ACCENTS"):
        LeaveOneAccentOutResult(
            family="ellipse",
            search_strategy="grid",
            scoring_metric="procrustes",
            distances_by_accent={"unknown": {HEBREW_LETTERS[0]: 0.1}},
            mean_distance_by_accent={"unknown": 0.1},
            best_candidate_id_by_accent={"unknown": candidate_id},
            exit_gate=None,
        )
    with pytest.raises(ValidationError, match="constants.HEBREW_LETTERS"):
        LeaveOneAccentOutResult(
            family="ellipse",
            search_strategy="grid",
            scoring_metric="procrustes",
            distances_by_accent={"ashkenazi": {"alef": 0.1}},
            mean_distance_by_accent={"ashkenazi": 0.1},
            best_candidate_id_by_accent={"ashkenazi": candidate_id},
            exit_gate=None,
        )
    with pytest.raises(ValidationError, match="finite and non-negative"):
        LeaveOneAccentOutResult(
            family="ellipse",
            search_strategy="grid",
            scoring_metric="procrustes",
            distances_by_accent={"ashkenazi": {HEBREW_LETTERS[0]: math.nan}},
            mean_distance_by_accent={"ashkenazi": 0.1},
            best_candidate_id_by_accent={"ashkenazi": candidate_id},
            exit_gate=None,
        )
    with pytest.raises(ValidationError, match="mean distances"):
        LeaveOneAccentOutResult(
            family="ellipse",
            search_strategy="grid",
            scoring_metric="procrustes",
            distances_by_accent={"ashkenazi": {HEBREW_LETTERS[0]: 0.1}},
            mean_distance_by_accent={"ashkenazi": -0.1},
            best_candidate_id_by_accent={"ashkenazi": candidate_id},
            exit_gate=None,
        )
    with pytest.raises(ValidationError, match="exit-gate"):
        LeaveOneAccentOutResult(
            family="ellipse",
            search_strategy="grid",
            scoring_metric="procrustes",
            distances_by_accent={"ashkenazi": {HEBREW_LETTERS[0]: 0.1}},
            mean_distance_by_accent={"ashkenazi": 0.1},
            best_candidate_id_by_accent={"ashkenazi": candidate_id},
            exit_gate=ExitGateResult(
                passed=False,
                accents_passed=0,
                letters_required=11,
                per_accent_pass_counts={"chabad": 0},
            ),
        )
