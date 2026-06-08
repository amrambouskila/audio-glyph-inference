"""Tests for src/models/live_loop_evidence.py."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError
from src.constants import GLYPH_FORMS
from src.models.live_loop_evidence import LiveLoopEvidence

CANDIDATE_ID = UUID("22222222-2222-2222-2222-222222222222")
GLYPH_ID = UUID("44444444-4444-4444-4444-444444444444")


def _evidence_payload() -> dict[str, object]:
    return {
        "tested_at": datetime(2026, 4, 16, tzinfo=UTC),
        "browser": "Chromium 124",
        "candidate_id": CANDIDATE_ID,
        "score_rate_threshold_hz": 10.0,
        "score_rate_hz_by_letter": {glyph_form: 12.5 for glyph_form in GLYPH_FORMS},
        "score_updates_by_letter": {glyph_form: 25 for glyph_form in GLYPH_FORMS},
        "glyph_target_id_by_letter": {glyph_form: GLYPH_ID for glyph_form in GLYPH_FORMS},
        "visible_score_by_letter": {glyph_form: True for glyph_form in GLYPH_FORMS},
    }


def test_live_loop_evidence_accepts_complete_all_letter_run() -> None:
    evidence = LiveLoopEvidence(**_evidence_payload())

    assert evidence.candidate_id == CANDIDATE_ID
    assert set(evidence.score_rate_hz_by_letter) == set(GLYPH_FORMS)


def test_live_loop_evidence_rejects_missing_or_unknown_letter_keys() -> None:
    payload = _evidence_payload()
    rates = dict(payload["score_rate_hz_by_letter"])
    rates.pop(GLYPH_FORMS[0])
    payload["score_rate_hz_by_letter"] = rates

    with pytest.raises(ValidationError, match="constants.GLYPH_FORMS"):
        LiveLoopEvidence(**payload)

    payload = _evidence_payload()
    visible = dict(payload["visible_score_by_letter"])
    visible["not-a-letter"] = True
    payload["visible_score_by_letter"] = visible

    with pytest.raises(ValidationError, match="constants.GLYPH_FORMS"):
        LiveLoopEvidence(**payload)


def test_live_loop_evidence_rejects_failed_observations() -> None:
    payload = _evidence_payload()
    rates = dict(payload["score_rate_hz_by_letter"])
    rates[GLYPH_FORMS[0]] = 9.99
    payload["score_rate_hz_by_letter"] = rates

    with pytest.raises(ValidationError, match="meet the threshold"):
        LiveLoopEvidence(**payload)

    payload = _evidence_payload()
    updates = dict(payload["score_updates_by_letter"])
    updates[GLYPH_FORMS[0]] = 0
    payload["score_updates_by_letter"] = updates

    with pytest.raises(ValidationError, match="positive"):
        LiveLoopEvidence(**payload)

    payload = _evidence_payload()
    visible = dict(payload["visible_score_by_letter"])
    visible[GLYPH_FORMS[0]] = False
    payload["visible_score_by_letter"] = visible

    with pytest.raises(ValidationError, match="visible"):
        LiveLoopEvidence(**payload)
