"""Negative-results report rendering for Phase 3/5 writeups."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from src.models.feasibility_probe_result import FeasibilityProbeResult
from src.models.leaderboard_entry import LeaderboardEntry
from src.models.leave_one_accent_out_result import LeaveOneAccentOutResult
from src.models.live_loop_evidence import LiveLoopEvidence


def render_negative_results_report(
    leaderboards: Mapping[str, Sequence[LeaderboardEntry]],
    *,
    leave_one_accent_out: LeaveOneAccentOutResult | None = None,
    feasibility_probe: FeasibilityProbeResult | None = None,
    live_loop_evidence: LiveLoopEvidence | None = None,
    excluded_run_names: Sequence[str] = (),
    conclusion: str = "pending",
) -> str:
    """Render deterministic Markdown for negative-results documentation."""
    lines = [
        "# Negative Results Report",
        "",
        "## Status",
        "",
        "Scaffold only. No negative result is claimed until real Stage-7 recordings, calibrated thresholds, "
        "and leave-one-accent-out evaluation have been run.",
        "",
        "## Search Transcript Inputs",
        "",
        "- Data split: accent-disjoint leave-one-accent-out.",
        "- Candidate scope: shared-across-letters operators are the headline result; per-letter rows are "
        "lookup-ceiling diagnostics.",
        "- Verdict rule: FEASIBLE requires a shared operator to clear the held-out gate without collapsing to "
        "a lookup-like diagnostic.",
        "",
        "## Excluded Non-Empirical Runs",
        "",
    ]
    lines.extend(_excluded_run_lines(excluded_run_names))
    lines.extend(
        [
            "",
            "## Per-Family Leaderboards",
            "",
        ]
    )
    lines.extend(_leaderboard_lines(leaderboards))
    lines.extend(["", "## Leave-One-Accent-Out", ""])
    lines.extend(_loo_lines(leave_one_accent_out))
    lines.extend(["", "## Feasibility Probe", ""])
    lines.extend(_feasibility_lines(feasibility_probe))
    lines.extend(["", "## Browser Live Loop", ""])
    lines.extend(_live_loop_lines(live_loop_evidence))
    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- FEASIBLE: a shared candidate clears the exit gate on held-out accents and beats lookup diagnostics.",
            "- TRIVIAL_LOOKUP: low distance is explained by per-letter structure rather than a shared operator.",
            "- NO_FIT: no shared candidate clears the calibrated held-out thresholds.",
            "",
            "## Conclusion",
            "",
            conclusion,
        ]
    )
    return "\n".join(lines) + "\n"


def _leaderboard_lines(leaderboards: Mapping[str, Sequence[LeaderboardEntry]]) -> list[str]:
    if not leaderboards:
        return ["No experiment ledger rows supplied."]
    lines: list[str] = []
    for family in sorted(leaderboards):
        lines.extend(
            [
                f"### {family}",
                "",
                "| rank | run | strategy | held_out_accent | distance | lookup_ratio | simplicity | candidate_id |",
                "| ---: | --- | --- | --- | ---: | ---: | ---: | --- |",
            ]
        )
        for rank, entry in enumerate(leaderboards[family], start=1):
            lines.append(
                "| "
                f"{rank} | {entry.run_name} | {entry.search_strategy} | "
                f"{entry.held_out_accent or 'none'} | {_format_float(entry.mean_shape_distance)} | "
                f"{_format_float(entry.lookup_ratio)} | {_format_float(entry.simplicity_score)} | "
                f"{entry.candidate_id} |"
            )
        lines.append("")
    return lines[:-1]


def _excluded_run_lines(excluded_run_names: Sequence[str]) -> list[str]:
    if not excluded_run_names:
        return ["No run names were excluded by the manifest."]
    return [f"- {name}" for name in sorted(excluded_run_names)]


def _loo_lines(result: LeaveOneAccentOutResult | None) -> list[str]:
    if result is None:
        return ["Leave-one-accent-out results are pending real Stage-7 recordings."]
    lines = [
        f"- Family: {result.family}",
        f"- Strategy: {result.search_strategy}",
        f"- Metric: {result.scoring_metric}",
        "",
        "| held_out_accent | mean_distance | best_candidate_id |",
        "| --- | ---: | --- |",
    ]
    for accent in sorted(result.mean_distance_by_accent):
        lines.append(
            "| "
            f"{accent} | {_format_float(result.mean_distance_by_accent[accent])} | "
            f"{result.best_candidate_id_by_accent[accent]} |"
        )
    lines.extend(["", "| held_out_accent | letter | distance |", "| --- | --- | ---: |"])
    for accent in sorted(result.distances_by_accent):
        for letter in sorted(result.distances_by_accent[accent]):
            lines.append(f"| {accent} | {letter} | {_format_float(result.distances_by_accent[accent][letter])} |")
    if result.exit_gate is not None:
        lines.extend(
            [
                "",
                f"- Exit gate passed: {result.exit_gate.passed}",
                f"- Accents passed: {result.exit_gate.accents_passed}",
                f"- Letters required per accent: {result.exit_gate.letters_required}",
                "",
                "| held_out_accent | letters_within_threshold |",
                "| --- | ---: |",
            ]
        )
        for accent in sorted(result.exit_gate.per_accent_pass_counts):
            lines.append(f"| {accent} | {result.exit_gate.per_accent_pass_counts[accent]} |")
    return lines


def _feasibility_lines(result: FeasibilityProbeResult | None) -> list[str]:
    if result is None:
        return ["Feasibility-probe verdict is pending real Stage-7 recordings and calibrated rho_min."]
    return [
        f"- Verdict: {result.verdict}",
        f"- Probe in/out: {_format_float(result.d_probe_in)} / {_format_float(result.d_probe_out)}",
        f"- Per-letter constant in/out: {_format_float(result.d_const_in)} / {_format_float(result.d_const_out)}",
        f"- Global constant in: {_format_float(result.d_global_in)}",
        f"- Lookup delta: {_format_float(result.delta_lookup)}",
        f"- Overfit ratio: {_format_float(result.overfit_ratio)}",
        f"- Lookup ratio: {_format_float(result.r_track)}",
    ]


def _live_loop_lines(result: LiveLoopEvidence | None) -> list[str]:
    if result is None:
        return ["Browser live-loop evidence is pending user testing across all Hebrew glyph forms."]
    minimum_rate = min(result.score_rate_hz_by_letter.values())
    lines = [
        f"- Browser: {result.browser}",
        f"- Candidate: {result.candidate_id}",
        f"- Tested at: {result.tested_at.isoformat()}",
        f"- Minimum observed score rate: {_format_float(minimum_rate)} Hz",
        f"- Required score rate: {_format_float(result.score_rate_threshold_hz)} Hz",
        "",
        "| letter | score_rate_hz | score_updates | glyph_target_id |",
        "| --- | ---: | ---: | --- |",
    ]
    for letter in sorted(result.score_rate_hz_by_letter):
        lines.append(
            "| "
            f"{letter} | {_format_float(result.score_rate_hz_by_letter[letter])} | "
            f"{result.score_updates_by_letter[letter]} | {result.glyph_target_id_by_letter[letter]} |"
        )
    return lines


def _format_float(value: float) -> str:
    return f"{value:.6g}"
