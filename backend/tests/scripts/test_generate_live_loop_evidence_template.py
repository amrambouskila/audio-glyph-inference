"""Tests for scripts/generate_live_loop_evidence_template.py."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError
from scripts.generate_live_loop_evidence_template import live_loop_evidence_template, main
from src.constants import GLYPH_FORMS
from src.models.live_loop_evidence import LiveLoopEvidence

CANDIDATE_ID = UUID("22222222-2222-2222-2222-222222222222")


def test_live_loop_evidence_template_contains_every_letter() -> None:
    template = live_loop_evidence_template(
        candidate_id=CANDIDATE_ID,
        browser="Chromium 124",
        score_rate_threshold_hz=10.0,
        tested_at=datetime(2026, 4, 16, tzinfo=UTC),
    )

    assert template["tested_at"] == "2026-04-16T00:00:00Z"
    assert template["browser"] == "Chromium 124"
    assert template["candidate_id"] == "22222222-2222-2222-2222-222222222222"
    assert set(template["score_rate_hz_by_letter"]) == set(GLYPH_FORMS)
    assert set(template["score_updates_by_letter"]) == set(GLYPH_FORMS)
    assert set(template["glyph_target_id_by_letter"]) == set(GLYPH_FORMS)
    assert set(template["visible_score_by_letter"]) == set(GLYPH_FORMS)
    assert all(rate == 0.0 for rate in template["score_rate_hz_by_letter"].values())
    assert all(updates == 0 for updates in template["score_updates_by_letter"].values())
    assert all(glyph_id == "" for glyph_id in template["glyph_target_id_by_letter"].values())
    assert not any(template["visible_score_by_letter"].values())


def test_live_loop_evidence_template_is_not_valid_before_observations() -> None:
    template = live_loop_evidence_template(
        candidate_id=CANDIDATE_ID,
        browser="Chromium 124",
        score_rate_threshold_hz=10.0,
        tested_at=datetime(2026, 4, 16, tzinfo=UTC),
    )

    with pytest.raises(ValidationError):
        LiveLoopEvidence(**template)


def test_main_writes_template_file(tmp_path: Path) -> None:
    output_path = tmp_path / "live-loop-evidence.json"

    assert (
        main(
            [
                "--candidate-id",
                "22222222-2222-2222-2222-222222222222",
                "--browser",
                "Chromium 124",
                "--score-rate-threshold-hz",
                "10.0",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    template = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(template["score_rate_hz_by_letter"]) == set(GLYPH_FORMS)


def test_main_prints_template_to_stdout(capsys) -> None:
    assert (
        main(
            [
                "--candidate-id",
                "22222222-2222-2222-2222-222222222222",
                "--browser",
                "Chromium 124",
                "--score-rate-threshold-hz",
                "10.0",
            ]
        )
        == 0
    )

    template = json.loads(capsys.readouterr().out)
    assert template["browser"] == "Chromium 124"


@pytest.mark.parametrize(
    ("option", "value"),
    (
        ("--candidate-id", "not-a-uuid"),
        ("--score-rate-threshold-hz", "0"),
        ("--score-rate-threshold-hz", "-1"),
        ("--score-rate-threshold-hz", "nan"),
    ),
)
def test_main_rejects_invalid_top_level_fields(option: str, value: str) -> None:
    args = [
        "--candidate-id",
        "22222222-2222-2222-2222-222222222222",
        "--browser",
        "Chromium 124",
        "--score-rate-threshold-hz",
        "10.0",
    ]
    args[args.index(option) + 1] = value

    with pytest.raises(SystemExit):
        main(args)


def test_script_file_is_imported_from_backend_scripts() -> None:
    module = sys.modules["scripts.generate_live_loop_evidence_template"]
    assert Path(module.__file__).name == "generate_live_loop_evidence_template.py"
