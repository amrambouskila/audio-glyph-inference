"""Tests for src/simulation/negative_results.py."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from src.constants import GLYPH_FORMS, HEBREW_LETTERS
from src.models.exit_gate_result import ExitGateResult
from src.models.feasibility_probe_result import FeasibilityProbeResult
from src.models.leaderboard_entry import LeaderboardEntry
from src.models.leave_one_accent_out_result import LeaveOneAccentOutResult
from src.models.live_loop_evidence import LiveLoopEvidence
from src.simulation.negative_results import (
    _excluded_run_lines,
    _feasibility_lines,
    _format_float,
    _leaderboard_lines,
    _live_loop_lines,
    _loo_lines,
    render_negative_results_report,
)

RUN_ID = UUID("11111111-1111-1111-1111-111111111111")
BEST_ID = UUID("22222222-2222-2222-2222-222222222222")
ALT_ID = UUID("33333333-3333-3333-3333-333333333333")
GLYPH_ID = UUID("44444444-4444-4444-4444-444444444444")
ALEF = HEBREW_LETTERS[0]
BET = HEBREW_LETTERS[1]


def _entry(candidate_id: UUID, distance: float, *, accent: str | None = "chabad") -> LeaderboardEntry:
    return LeaderboardEntry(
        family="fourier_series",
        run_id=RUN_ID,
        run_name="run-a",
        candidate_id=candidate_id,
        search_strategy="grid",
        scoring_metric="procrustes",
        held_out_accent=accent,
        shared_across_letters=True,
        mean_shape_distance=distance,
        simplicity_score=0.8,
        interpretability_score=0.7,
        lookup_ratio=0.2,
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )


def _loo_result() -> LeaveOneAccentOutResult:
    return LeaveOneAccentOutResult(
        family="fourier_series",
        search_strategy="grid",
        scoring_metric="procrustes",
        distances_by_accent={"chabad": {ALEF: 0.12, BET: 0.34}},
        mean_distance_by_accent={"chabad": 0.23},
        best_candidate_id_by_accent={"chabad": BEST_ID},
        exit_gate=ExitGateResult(
            passed=False,
            accents_passed=0,
            letters_required=2,
            per_accent_pass_counts={"chabad": 1},
        ),
    )


def _feasibility() -> FeasibilityProbeResult:
    return FeasibilityProbeResult(
        verdict="NO_FIT",
        d_probe_in=0.1,
        d_probe_out=0.2,
        d_const_in=0.3,
        d_const_out=0.4,
        d_global_in=0.5,
        delta_lookup=0.2,
        overfit_ratio=2.0,
        r_track=0.6,
    )


def _live_loop() -> LiveLoopEvidence:
    return LiveLoopEvidence(
        tested_at=datetime(2026, 4, 16, tzinfo=UTC),
        browser="Chromium 124",
        candidate_id=BEST_ID,
        score_rate_threshold_hz=10.0,
        score_rate_hz_by_letter={glyph_form: 12.5 for glyph_form in GLYPH_FORMS},
        score_updates_by_letter={glyph_form: 25 for glyph_form in GLYPH_FORMS},
        glyph_target_id_by_letter={glyph_form: GLYPH_ID for glyph_form in GLYPH_FORMS},
        visible_score_by_letter={glyph_form: True for glyph_form in GLYPH_FORMS},
    )


def test_render_negative_results_report_returns_pending_scaffold_for_empty_inputs() -> None:
    report = render_negative_results_report({})

    assert "# Negative Results Report" in report
    assert "Scaffold only" in report
    assert "No experiment ledger rows supplied." in report
    assert "No run names were excluded by the manifest." in report
    assert "Leave-one-accent-out results are pending" in report
    assert "Feasibility-probe verdict is pending" in report
    assert "Browser live-loop evidence is pending" in report
    assert report.endswith("pending\n")


def test_render_negative_results_report_includes_all_result_sections() -> None:
    report = render_negative_results_report(
        {"fourier_series": [_entry(BEST_ID, 0.123456789), _entry(ALT_ID, 0.2, accent=None)]},
        leave_one_accent_out=_loo_result(),
        feasibility_probe=_feasibility(),
        live_loop_evidence=_live_loop(),
        excluded_run_names=("live-smoke-seed",),
        conclusion="No shared fit cleared the gate.",
    )

    assert "- live-smoke-seed" in report
    assert "| 1 | run-a | grid | chabad | 0.123457 | 0.2 | 0.8 |" in report
    assert "| 2 | run-a | grid | none | 0.2 | 0.2 | 0.8 |" in report
    assert "| chabad | 0.23 | 22222222-2222-2222-2222-222222222222 |" in report
    assert f"| chabad | {ALEF} | 0.12 |" in report
    assert "- Exit gate passed: False" in report
    assert "- Verdict: NO_FIT" in report
    assert "- Minimum observed score rate: 12.5 Hz" in report
    assert f"| {ALEF} | 12.5 | 25 | 44444444-4444-4444-4444-444444444444 |" in report
    assert report.endswith("No shared fit cleared the gate.\n")


def test_helper_lines_cover_pending_and_present_branches() -> None:
    assert _leaderboard_lines({}) == ["No experiment ledger rows supplied."]
    assert _excluded_run_lines(()) == ["No run names were excluded by the manifest."]
    assert _excluded_run_lines(("z-run", "a-run")) == ["- a-run", "- z-run"]
    assert _loo_lines(None) == ["Leave-one-accent-out results are pending real Stage-7 recordings."]
    loo_without_gate = _loo_result().model_copy(update={"exit_gate": None})
    assert "Exit gate passed" not in "\n".join(_loo_lines(loo_without_gate))
    assert _feasibility_lines(None) == [
        "Feasibility-probe verdict is pending real Stage-7 recordings and calibrated rho_min."
    ]
    assert _live_loop_lines(None) == [
        "Browser live-loop evidence is pending user testing across all Hebrew glyph forms."
    ]
    assert _format_float(1.0 / 3.0) == "0.333333"
