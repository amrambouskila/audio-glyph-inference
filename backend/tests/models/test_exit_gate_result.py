"""Tests for src/models/exit_gate_result.py — round-trip + field validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.models.exit_gate_result import ExitGateResult


def test_round_trip() -> None:
    result = ExitGateResult(
        passed=True,
        accents_passed=2,
        letters_required=11,
        per_accent_pass_counts={"yemenite": 12, "chabad": 11},
    )
    assert ExitGateResult.model_validate(result.model_dump()) == result


def test_failing_verdict_fields() -> None:
    result = ExitGateResult(passed=False, accents_passed=0, letters_required=11, per_accent_pass_counts={})
    assert result.passed is False
    assert result.accents_passed == 0
    assert result.per_accent_pass_counts == {}


def test_exit_gate_rejects_invalid_counts() -> None:
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        ExitGateResult(passed=False, accents_passed=-1, letters_required=11, per_accent_pass_counts={})
    with pytest.raises(ValidationError, match="per_accent_pass_counts"):
        ExitGateResult(passed=False, accents_passed=0, letters_required=11, per_accent_pass_counts={"chabad": -1})
    with pytest.raises(ValidationError, match="accents_passed"):
        ExitGateResult(passed=True, accents_passed=2, letters_required=11, per_accent_pass_counts={"chabad": 11})
