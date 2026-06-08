"""Tests for scripts/render_phase5_report.py."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from scripts.render_phase5_report import main, render_report_from_manifest
from src.constants import ACCENTS, GLYPH_FORMS, HEBREW_LETTERS, NUM_AUDIO_FORMS
from src.models.experiment_run import ExperimentRun
from src.models.transform_candidate import TransformCandidate
from src.simulation.experiment_tracker import ExperimentTracker

BEST_ID = UUID("22222222-2222-2222-2222-222222222222")


def _run() -> ExperimentRun:
    return ExperimentRun(
        id=uuid4(),
        name="phase5-fourier",
        family="fourier_series",
        search_strategy="grid",
        dataset_split="train",
        scoring_metric="procrustes",
        regularization_weight=0.01,
        held_out_accent="chabad",
        rng_seed=7,
        font_name="StamAshkenazCLM.ttf",
        config_snapshot={"search_grid_resolution": 5},
        max_evaluations=5,
        started_at=datetime(2026, 4, 16, tzinfo=UTC),
        completed_at=datetime(2026, 4, 16, 0, 1, tzinfo=UTC),
    )


def _smoke_run() -> ExperimentRun:
    return _run().model_copy(update={"id": uuid4(), "name": "live-smoke-seed", "held_out_accent": None})


def _candidate() -> TransformCandidate:
    return TransformCandidate(
        id=BEST_ID,
        family="fourier_series",
        theta={"rank_r": 1},
        shared_across_letters=True,
        interpretability_score=0.7,
        simplicity_score=0.8,
        mean_shape_distance=0.12,
        lookup_ratio=0.2,
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )


def _write_manifest(tmp_path: Path, runs_dir: Path) -> Path:
    loo_path = tmp_path / "loo.json"
    feasibility_path = tmp_path / "probe.json"
    live_loop_path = tmp_path / "live-loop.json"
    loo_path.write_text(
        json.dumps(
            {
                "family": "fourier_series",
                "search_strategy": "grid",
                "scoring_metric": "procrustes",
                "distances_by_accent": {"chabad": {HEBREW_LETTERS[0]: 0.12}},
                "mean_distance_by_accent": {"chabad": 0.12},
                "best_candidate_id_by_accent": {"chabad": str(BEST_ID)},
                "exit_gate": {
                    "passed": False,
                    "accents_passed": 0,
                    "letters_required": 11,
                    "per_accent_pass_counts": {"chabad": 1},
                },
            }
        ),
        encoding="utf-8",
    )
    feasibility_path.write_text(
        json.dumps(
            {
                "verdict": "NO_FIT",
                "d_probe_in": 0.1,
                "d_probe_out": 0.2,
                "d_const_in": 0.3,
                "d_const_out": 0.4,
                "d_global_in": 0.5,
                "delta_lookup": 0.2,
                "overfit_ratio": 2.0,
                "r_track": 0.6,
            }
        ),
        encoding="utf-8",
    )
    live_loop_path.write_text(
        json.dumps(
            {
                "tested_at": "2026-04-16T00:00:00Z",
                "browser": "Chromium 124",
                "candidate_id": str(BEST_ID),
                "score_rate_threshold_hz": 10.0,
                "score_rate_hz_by_letter": {glyph_form: 12.5 for glyph_form in GLYPH_FORMS},
                "score_updates_by_letter": {glyph_form: 25 for glyph_form in GLYPH_FORMS},
                "glyph_target_id_by_letter": {glyph_form: str(uuid4()) for glyph_form in GLYPH_FORMS},
                "visible_score_by_letter": {glyph_form: True for glyph_form in GLYPH_FORMS},
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    _write_manifest_payload(
        manifest_path,
        tmp_path,
        runs_dir,
        {
            "leave_one_accent_out_result": str(loo_path),
            "feasibility_probe_result": str(feasibility_path),
            "live_loop_evidence": str(live_loop_path),
            "conclusion": "Real-data report rendered.",
        },
    )
    return manifest_path


def _write_manifest_payload(
    manifest_path: Path,
    repo_root: Path,
    runs_dir: Path,
    overrides: dict[str, object] | None = None,
) -> None:
    writeup_path = repo_root / "docs" / "writeup.md"
    notebook_path = repo_root / "notebooks" / "phase5_reproducibility.ipynb"
    font_path = repo_root / "backend" / "data" / "fonts" / "StamAshkenazCLM.ttf"
    writeup_path.parent.mkdir(parents=True, exist_ok=True)
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    font_path.parent.mkdir(parents=True, exist_ok=True)
    writeup_path.write_text("# Writeup\n", encoding="utf-8")
    notebook_path.write_text("{}", encoding="utf-8")
    font_path.write_bytes(b"font")
    repetitions = 5
    payload: dict[str, object] = {
        "name": "phase5_pending_real_data",
        "status": "pending_real_recordings",
        "purpose": "Render pending Phase-5 report.",
        "runs_dir": str(runs_dir),
        "report_command": "uv run python scripts/render_phase5_report.py",
        "conclusion": "pending",
        "data_requirements": {
            "audio_source": "user_m4a_uploads",
            "speaker_count": 1,
            "accents": list(ACCENTS),
            "base_letters": "backend/src/constants.py::HEBREW_LETTERS",
            "audio_forms": "backend/src/constants.py::AUDIO_FORM_KEYS",
            "glyph_forms": list(GLYPH_FORMS),
            "repetitions_per_accent_letter": repetitions,
            "total_expected_audio_samples": len(ACCENTS) * NUM_AUDIO_FORMS * repetitions,
            "target_font": str(font_path),
        },
        "pipeline": ["Replay ledgers"],
        "families": [
            "fourier_series",
            "lissajous",
            "phase_space_embedding",
            "dynamical_system",
            "symbolic_regression",
        ],
        "strategies": ["grid", "cma-es", "bayesian", "symbolic-regression"],
        "distance_metrics": ["procrustes", "chamfer", "frechet"],
        "headline_candidate_rule": "Only shared candidates count.",
        "excluded_run_names": ["live-smoke-seed"],
        "pending_external_inputs": ["Stage-7 real recordings"],
        "writeup": str(writeup_path),
        "notebook": str(notebook_path),
    }
    if overrides is not None:
        payload.update(overrides)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")


def test_render_report_from_manifest_replays_ledgers_and_optional_results(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    tracker = ExperimentTracker(runs_dir)
    run = _run()
    tracker.log_run(run)
    tracker.log_candidate(str(run.id), _candidate())
    manifest_path = _write_manifest(tmp_path, runs_dir)

    report = render_report_from_manifest(manifest_path, repo_root=tmp_path)

    assert "| 1 | phase5-fourier | grid | chabad | 0.12 | 0.2 | 0.8 |" in report
    assert "| chabad | 0.12 | 22222222-2222-2222-2222-222222222222 |" in report
    assert f"| chabad | {HEBREW_LETTERS[0]} | 0.12 |" in report
    assert "- Verdict: NO_FIT" in report
    assert "- Minimum observed score rate: 12.5 Hz" in report
    assert "- live-smoke-seed" in report
    assert report.endswith("Real-data report rendered.\n")


def test_render_report_from_manifest_excludes_non_empirical_smoke_runs(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    tracker = ExperimentTracker(runs_dir)
    real_run = _run()
    smoke_run = _smoke_run()
    tracker.log_run(real_run)
    tracker.log_candidate(str(real_run.id), _candidate())
    tracker.log_run(smoke_run)
    tracker.log_candidate(
        str(smoke_run.id), _candidate().model_copy(update={"id": uuid4(), "mean_shape_distance": 0.01})
    )
    manifest_path = _write_manifest(tmp_path, runs_dir)

    report = render_report_from_manifest(manifest_path, repo_root=tmp_path)

    assert "phase5-fourier" in report
    assert "- live-smoke-seed" in report
    assert "| 1 | live-smoke-seed" not in report


def test_main_writes_output_file(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    manifest_path = _write_manifest(tmp_path, runs_dir)
    output_path = tmp_path / "report.md"

    assert main(["--manifest", str(manifest_path), "--repo-root", str(tmp_path), "--output", str(output_path)]) == 0

    report = output_path.read_text(encoding="utf-8")
    assert "No experiment ledger rows supplied." in report
    assert report.endswith("Real-data report rendered.\n")


def test_main_prints_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_manifest_payload(manifest_path, tmp_path, tmp_path / "runs")

    assert main(["--manifest", str(manifest_path), "--repo-root", str(tmp_path)]) == 0

    assert "# Negative Results Report" in capsys.readouterr().out


def test_render_report_from_manifest_does_not_create_missing_runs_dir(tmp_path: Path) -> None:
    runs_dir = tmp_path / "missing-runs"
    manifest_path = tmp_path / "manifest.json"
    _write_manifest_payload(manifest_path, tmp_path, runs_dir)

    report = render_report_from_manifest(manifest_path, repo_root=tmp_path)

    assert "No experiment ledger rows supplied." in report
    assert not runs_dir.exists()


def test_committed_pending_manifest_is_valid() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    manifest_path = repo_root / "backend" / "experiments" / "manifests" / "phase5_pending_real_data.json"

    report = render_report_from_manifest(manifest_path, repo_root=repo_root)

    assert "Scaffold only." in report
    assert report.endswith("pending\n")


def test_committed_phase5_notebook_uses_manifest_renderer_and_exclusions() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    notebook_path = repo_root / "notebooks" / "phase5_reproducibility.ipynb"

    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source_text = "\n".join(
        "".join(cell.get("source", [])) for cell in notebook["cells"] if cell.get("cell_type") == "code"
    )

    assert "render_report_from_manifest" in source_text
    assert "build_family_leaderboards" in source_text
    assert "excluded_run_names" in source_text
    assert "pd.DataFrame" in source_text


def test_manifest_validation_errors(tmp_path: Path) -> None:
    scalar_manifest = tmp_path / "scalar.json"
    scalar_manifest.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        render_report_from_manifest(scalar_manifest, repo_root=tmp_path)

    bad_path_manifest = tmp_path / "bad-path.json"
    _write_manifest_payload(bad_path_manifest, tmp_path, tmp_path / "runs", {"runs_dir": 1})
    with pytest.raises(ValueError, match="runs_dir"):
        render_report_from_manifest(bad_path_manifest, repo_root=tmp_path)

    bad_conclusion_manifest = tmp_path / "bad-conclusion.json"
    _write_manifest_payload(bad_conclusion_manifest, tmp_path, tmp_path / "runs", {"conclusion": 1})
    with pytest.raises(ValueError, match="conclusion"):
        render_report_from_manifest(bad_conclusion_manifest, repo_root=tmp_path)

    missing_required_manifest = tmp_path / "missing-required.json"
    _write_manifest_payload(missing_required_manifest, tmp_path, tmp_path / "runs")
    payload = json.loads(missing_required_manifest.read_text(encoding="utf-8"))
    del payload["purpose"]
    missing_required_manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="purpose"):
        render_report_from_manifest(missing_required_manifest, repo_root=tmp_path)

    bad_total_manifest = tmp_path / "bad-total.json"
    bad_requirements = {
        "audio_source": "user_m4a_uploads",
        "speaker_count": 1,
        "accents": list(ACCENTS),
        "base_letters": "backend/src/constants.py::HEBREW_LETTERS",
        "audio_forms": "backend/src/constants.py::AUDIO_FORM_KEYS",
        "glyph_forms": list(GLYPH_FORMS),
        "repetitions_per_accent_letter": 5,
        "total_expected_audio_samples": 1,
        "target_font": "backend/data/fonts/StamAshkenazCLM.ttf",
    }
    _write_manifest_payload(bad_total_manifest, tmp_path, tmp_path / "runs", {"data_requirements": bad_requirements})
    with pytest.raises(ValueError, match="total_expected_audio_samples"):
        render_report_from_manifest(bad_total_manifest, repo_root=tmp_path)

    bad_font_manifest = tmp_path / "bad-font.json"
    bad_font_requirements = dict(bad_requirements)
    bad_font_requirements["total_expected_audio_samples"] = len(ACCENTS) * NUM_AUDIO_FORMS * 5
    bad_font_requirements["target_font"] = "backend/data/fonts/missing.ttf"
    _write_manifest_payload(
        bad_font_manifest, tmp_path, tmp_path / "runs", {"data_requirements": bad_font_requirements}
    )
    with pytest.raises(ValueError, match="target_font"):
        render_report_from_manifest(bad_font_manifest, repo_root=tmp_path)

    bad_family_manifest = tmp_path / "bad-family.json"
    _write_manifest_payload(bad_family_manifest, tmp_path, tmp_path / "runs", {"families": ["lookup_table"]})
    with pytest.raises(ValueError, match="families"):
        render_report_from_manifest(bad_family_manifest, repo_root=tmp_path)

    missing_strategy_manifest = tmp_path / "missing-strategy.json"
    _write_manifest_payload(
        missing_strategy_manifest,
        tmp_path,
        tmp_path / "runs",
        {"strategies": ["grid", "cma-es", "symbolic-regression"]},
    )
    with pytest.raises(ValueError, match="strategies"):
        render_report_from_manifest(missing_strategy_manifest, repo_root=tmp_path)

    bad_writeup_manifest = tmp_path / "bad-writeup.json"
    _write_manifest_payload(bad_writeup_manifest, tmp_path, tmp_path / "runs", {"writeup": "docs/missing.md"})
    with pytest.raises(ValueError, match="writeup"):
        render_report_from_manifest(bad_writeup_manifest, repo_root=tmp_path)

    bad_excluded_runs_manifest = tmp_path / "bad-excluded-runs.json"
    _write_manifest_payload(
        bad_excluded_runs_manifest,
        tmp_path,
        tmp_path / "runs",
        {"excluded_run_names": ["live-smoke-seed", ""]},
    )
    with pytest.raises(ValueError, match="excluded_run_names"):
        render_report_from_manifest(bad_excluded_runs_manifest, repo_root=tmp_path)


def test_optional_result_files_are_validated_before_rendering(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    bad_loo_path = tmp_path / "bad-loo.json"
    bad_loo_path.write_text(
        json.dumps(
            {
                "family": "fourier_series",
                "search_strategy": "grid",
                "scoring_metric": "procrustes",
                "distances_by_accent": {"unknown": {HEBREW_LETTERS[0]: 0.12}},
                "mean_distance_by_accent": {"unknown": 0.12},
                "best_candidate_id_by_accent": {"unknown": str(BEST_ID)},
                "exit_gate": None,
            }
        ),
        encoding="utf-8",
    )
    bad_loo_manifest = tmp_path / "bad-loo-manifest.json"
    _write_manifest_payload(
        bad_loo_manifest,
        tmp_path,
        runs_dir,
        {"leave_one_accent_out_result": str(bad_loo_path)},
    )
    with pytest.raises(ValueError, match="constants.ACCENTS"):
        render_report_from_manifest(bad_loo_manifest, repo_root=tmp_path)

    bad_probe_path = tmp_path / "bad-probe.json"
    bad_probe_path.write_text(
        json.dumps(
            {
                "verdict": "NO_FIT",
                "d_probe_in": 0.1,
                "d_probe_out": -0.2,
                "d_const_in": 0.3,
                "d_const_out": 0.4,
                "d_global_in": 0.5,
                "delta_lookup": 0.2,
                "overfit_ratio": 2.0,
                "r_track": 0.6,
            }
        ),
        encoding="utf-8",
    )
    bad_probe_manifest = tmp_path / "bad-probe-manifest.json"
    _write_manifest_payload(
        bad_probe_manifest,
        tmp_path,
        runs_dir,
        {"feasibility_probe_result": str(bad_probe_path)},
    )
    with pytest.raises(ValueError, match="finite and non-negative"):
        render_report_from_manifest(bad_probe_manifest, repo_root=tmp_path)

    bad_live_loop_path = tmp_path / "bad-live-loop.json"
    bad_live_loop_path.write_text(
        json.dumps(
            {
                "tested_at": "2026-04-16T00:00:00Z",
                "browser": "Chromium 124",
                "candidate_id": str(BEST_ID),
                "score_rate_threshold_hz": 10.0,
                "score_rate_hz_by_letter": {glyph_form: 12.5 for glyph_form in GLYPH_FORMS},
                "score_updates_by_letter": {glyph_form: 25 for glyph_form in GLYPH_FORMS},
                "glyph_target_id_by_letter": {glyph_form: str(uuid4()) for glyph_form in GLYPH_FORMS},
                "visible_score_by_letter": {glyph_form: True for glyph_form in GLYPH_FORMS[:-1]},
            }
        ),
        encoding="utf-8",
    )
    bad_live_loop_manifest = tmp_path / "bad-live-loop-manifest.json"
    _write_manifest_payload(
        bad_live_loop_manifest,
        tmp_path,
        runs_dir,
        {"live_loop_evidence": str(bad_live_loop_path)},
    )
    with pytest.raises(ValueError, match="constants.GLYPH_FORMS"):
        render_report_from_manifest(bad_live_loop_manifest, repo_root=tmp_path)


def test_script_file_is_imported_from_backend_scripts() -> None:
    assert Path(sys.modules["scripts.render_phase5_report"].__file__).name == "render_phase5_report.py"
