"""Render the Phase-5 report transcript from a reproducibility manifest."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, get_args, get_origin

from src.constants import ACCENTS, GLYPH_FORMS, NUM_AUDIO_FORMS
from src.models.experiment_run import ExperimentRun
from src.models.feasibility_probe_result import FeasibilityProbeResult
from src.models.leaderboard_entry import LeaderboardEntry
from src.models.leave_one_accent_out_result import LeaveOneAccentOutResult
from src.models.live_loop_evidence import LiveLoopEvidence
from src.simulation.experiment_tracker import ExperimentTracker
from src.simulation.leaderboard import build_family_leaderboards
from src.simulation.negative_results import render_negative_results_report
from src.simulation.transforms.family_registry import FAMILY_REGISTRY


def render_report_from_manifest(
    manifest_path: Path,
    *,
    repo_root: Path,
    runs_dir: Path | None = None,
) -> str:
    """Render deterministic Markdown from a Phase-5 manifest."""
    manifest = _load_json_object(manifest_path)
    _validate_manifest(manifest, repo_root)
    resolved_runs_dir = (
        runs_dir or _manifest_path(manifest, "runs_dir", repo_root) or repo_root / "backend" / "experiments"
    )
    tracker = ExperimentTracker(resolved_runs_dir, create=False)
    leaderboards = build_family_leaderboards(tracker)
    excluded_run_names = _manifest_string_sequence(manifest, "excluded_run_names", default=())
    leaderboards = _exclude_runs_by_name(leaderboards, excluded_run_names)
    leave_one_accent_out = _load_leave_one_accent_out(manifest, repo_root)
    feasibility_probe = _load_feasibility_probe(manifest, repo_root)
    live_loop_evidence = _load_live_loop_evidence(manifest, repo_root)
    conclusion = _manifest_string(manifest, "conclusion", default="pending")
    return render_negative_results_report(
        leaderboards,
        leave_one_accent_out=leave_one_accent_out,
        feasibility_probe=feasibility_probe,
        live_loop_evidence=live_loop_evidence,
        excluded_run_names=excluded_run_names,
        conclusion=conclusion,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Phase-5 report renderer."""
    parser = argparse.ArgumentParser(description="Render a Phase-5 Markdown report from a manifest.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--runs-dir", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    report = render_report_from_manifest(
        args.manifest,
        repo_root=args.repo_root,
        runs_dir=args.runs_dir,
    )
    if args.output is None:
        print(report, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    return 0


def _load_json_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _validate_manifest(manifest: dict[str, object], repo_root: Path) -> None:
    required_strings = (
        "name",
        "status",
        "purpose",
        "runs_dir",
        "report_command",
        "conclusion",
        "headline_candidate_rule",
    )
    for key in required_strings:
        _require_manifest_string(manifest, key)
    _validate_path_field(manifest, "writeup", repo_root)
    _validate_path_field(manifest, "notebook", repo_root)
    _validate_data_requirements(manifest, repo_root)
    _validate_string_sequence(manifest, "pipeline", allowed_values=(), require_all_allowed=False)
    _validate_string_sequence(manifest, "families", allowed_values=tuple(FAMILY_REGISTRY), require_all_allowed=True)
    _validate_string_sequence(
        manifest,
        "strategies",
        allowed_values=_literal_field_values("search_strategy"),
        require_all_allowed=True,
    )
    _validate_string_sequence(
        manifest,
        "distance_metrics",
        allowed_values=_literal_field_values("scoring_metric"),
        require_all_allowed=True,
    )
    _validate_string_sequence(manifest, "pending_external_inputs", allowed_values=(), require_all_allowed=False)
    if "excluded_run_names" in manifest:
        _validate_string_sequence(manifest, "excluded_run_names", allowed_values=(), require_all_allowed=False)


def _validate_data_requirements(manifest: dict[str, object], repo_root: Path) -> None:
    value = manifest.get("data_requirements")
    if not isinstance(value, dict):
        raise ValueError("manifest field 'data_requirements' must be an object")

    accents = value.get("accents")
    if accents != list(ACCENTS):
        raise ValueError("manifest data_requirements.accents must match constants.ACCENTS")

    base_letters = value.get("base_letters")
    if base_letters != "backend/src/constants.py::HEBREW_LETTERS":
        raise ValueError("manifest data_requirements.base_letters must reference constants.HEBREW_LETTERS")

    audio_forms = value.get("audio_forms")
    if audio_forms != "backend/src/constants.py::AUDIO_FORM_KEYS":
        raise ValueError("manifest data_requirements.audio_forms must reference constants.AUDIO_FORM_KEYS")

    glyph_forms = value.get("glyph_forms")
    if glyph_forms != list(GLYPH_FORMS):
        raise ValueError("manifest data_requirements.glyph_forms must match constants.GLYPH_FORMS")

    repetitions = value.get("repetitions_per_accent_letter")
    if not isinstance(repetitions, int) or repetitions <= 0:
        raise ValueError("manifest data_requirements.repetitions_per_accent_letter must be a positive integer")

    expected_total = value.get("total_expected_audio_samples")
    actual_total = len(ACCENTS) * NUM_AUDIO_FORMS * repetitions
    if expected_total != actual_total:
        raise ValueError("manifest data_requirements.total_expected_audio_samples does not match constants")

    required_values: tuple[tuple[str, object], ...] = (
        ("audio_source", "user_m4a_uploads"),
        ("speaker_count", 1),
    )
    for key, expected in required_values:
        if value.get(key) != expected:
            raise ValueError(f"manifest data_requirements.{key} must be {expected!r}")

    target_font = value.get("target_font")
    if not isinstance(target_font, str) or target_font == "":
        raise ValueError("manifest data_requirements.target_font must be a non-empty string")
    target_font_path = Path(target_font)
    if not target_font_path.is_absolute():
        target_font_path = repo_root / target_font_path
    if not target_font_path.exists():
        raise ValueError("manifest data_requirements.target_font must point to an existing path")


def _validate_string_sequence(
    manifest: dict[str, object],
    key: str,
    *,
    allowed_values: tuple[str, ...],
    require_all_allowed: bool,
) -> None:
    value = manifest.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"manifest field {key!r} must be a non-empty list of strings")
    if allowed_values and not set(value).issubset(allowed_values):
        raise ValueError(f"manifest field {key!r} must contain only {sorted(allowed_values)}")
    if allowed_values and require_all_allowed and set(value) != set(allowed_values):
        raise ValueError(f"manifest field {key!r} must contain {sorted(allowed_values)}")


def _validate_path_field(manifest: dict[str, object], key: str, repo_root: Path) -> None:
    path = _manifest_path(manifest, key, repo_root)
    if path is None or not path.exists():
        raise ValueError(f"manifest field {key!r} must point to an existing path")


def _literal_field_values(field_name: str) -> tuple[str, ...]:
    annotation = ExperimentRun.model_fields[field_name].annotation
    if get_origin(annotation) is not Literal:
        raise ValueError(f"ExperimentRun.{field_name} must be a Literal annotation")
    return tuple(value for value in get_args(annotation) if isinstance(value, str))


def _manifest_path(manifest: dict[str, object], key: str, repo_root: Path) -> Path | None:
    value = manifest.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"manifest field {key!r} must be a string path")
    path = Path(value)
    if path.is_absolute():
        return path
    return repo_root / path


def _manifest_string(manifest: dict[str, object], key: str, *, default: str) -> str:
    value = manifest.get(key, default)
    if not isinstance(value, str):
        raise ValueError(f"manifest field {key!r} must be a string")
    return value


def _manifest_string_sequence(
    manifest: dict[str, object],
    key: str,
    *,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = manifest.get(key, list(default))
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"manifest field {key!r} must be a list of non-empty strings")
    return tuple(value)


def _require_manifest_string(manifest: dict[str, object], key: str) -> str:
    if key not in manifest:
        raise ValueError(f"manifest field {key!r} is required")
    return _manifest_string(manifest, key, default="")


def _load_leave_one_accent_out(manifest: dict[str, object], repo_root: Path) -> LeaveOneAccentOutResult | None:
    path = _manifest_path(manifest, "leave_one_accent_out_result", repo_root)
    if path is None:
        return None
    return LeaveOneAccentOutResult(**_load_json_object(path))


def _load_feasibility_probe(manifest: dict[str, object], repo_root: Path) -> FeasibilityProbeResult | None:
    path = _manifest_path(manifest, "feasibility_probe_result", repo_root)
    if path is None:
        return None
    return FeasibilityProbeResult(**_load_json_object(path))


def _load_live_loop_evidence(manifest: dict[str, object], repo_root: Path) -> LiveLoopEvidence | None:
    path = _manifest_path(manifest, "live_loop_evidence", repo_root)
    if path is None:
        return None
    return LiveLoopEvidence(**_load_json_object(path))


def _exclude_runs_by_name(
    leaderboards: dict[str, list[LeaderboardEntry]],
    excluded_run_names: tuple[str, ...],
) -> dict[str, list[LeaderboardEntry]]:
    if not excluded_run_names:
        return leaderboards
    excluded = set(excluded_run_names)
    filtered: dict[str, list[LeaderboardEntry]] = {}
    for family, entries in leaderboards.items():
        family_entries = [entry for entry in entries if entry.run_name not in excluded]
        if family_entries:
            filtered[family] = family_entries
    return filtered


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
