"""Integration tests for src/api/routers/experiments.py."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
import soundfile as sf
from httpx import ASGITransport, AsyncClient
from pydantic import Field, ValidationError
from sqlalchemy import select
from src.api.main import create_app
from src.api.routers import experiments
from src.config import BackendSettings
from src.config_snapshot import config_snapshot
from src.data.orm.audio_sample_row import AudioSampleRow
from src.data.orm.experiment_run_row import ExperimentRunRow
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.paired_example_row import PairedExampleRow
from src.data.orm.transform_candidate_row import TransformCandidateRow
from src.models.experiment_create import ExperimentCreate
from src.models.transform_candidate import ThetaValue
from src.simulation.contour_io import save_contours

from tests.conftest import build_settings

SR = 44_100
N_POINTS = 256


def _tone(path: Path, frequency_hz: float) -> None:
    t = np.linspace(0.0, 2.0, int(SR * 2.0), endpoint=False)
    signal = 0.3 * np.sin(2.0 * np.pi * frequency_hz * t)
    sf.write(path, signal, SR)


def _ellipse(y_scale: float = 0.25) -> np.ndarray:
    t = 2.0 * np.pi * np.arange(N_POINTS) / N_POINTS
    return np.stack([0.5 * np.cos(t), y_scale * np.sin(t)], axis=1).astype(np.float64)


async def _seed_pair(
    db_session,
    tmp_path: Path,
    *,
    index: int,
    frequency_hz: float,
    accent: str = "ashkenazi",
) -> None:
    audio_path = tmp_path / f"sample-{index}.wav"
    contour_path = tmp_path / f"target-{index}.npz"
    _tone(audio_path, frequency_hz)
    save_contours(contour_path, [_ellipse()])
    audio = AudioSampleRow(
        id=uuid4(),
        letter=f"letter-{index}",
        speaker_id="owner",
        accent=accent,
        repetition=index,
        pronunciation_variant="plain",
        source="user",
        file_path=str(audio_path),
        sample_rate_hz=SR,
        duration_s=2.0,
        recorded_at=datetime(2026, 4, 16, tzinfo=UTC),
    )
    glyph = GlyphTargetRow(
        id=uuid4(),
        letter=f"letter-{index}",
        glyph_form=f"letter-{index}",
        font_name="StamAshkenazCLM.ttf",
        raster_size_px=256,
        contour_path=str(contour_path),
        num_points=N_POINTS,
        num_contours=1,
    )
    db_session.add_all([audio, glyph])
    await db_session.flush()
    db_session.add(
        PairedExampleRow(
            id=uuid4(),
            audio_sample_id=audio.id,
            glyph_target_id=glyph.id,
            letter=audio.letter,
            pronunciation_variant=audio.pronunciation_variant,
            glyph_form=glyph.glyph_form,
            split="train",
        )
    )
    await db_session.commit()


async def _client(db_engine, postgres_url: str, tmp_path: Path) -> AsyncClient:
    settings = build_settings(
        postgres_url,
        tmp_path,
        experiments_dir=tmp_path / "experiments",
        audio_active_speech_max_s=2.1,
    )
    app = create_app(settings=settings, engine=db_engine)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_create_list_and_get_experiment(client, db_session, db_engine, postgres_url, tmp_path) -> None:
    await _seed_pair(db_session, tmp_path, index=1, frequency_hz=440.0)
    await _seed_pair(db_session, tmp_path, index=2, frequency_hz=660.0)
    async with await _client(db_engine, postgres_url, tmp_path) as http_client:
        resp = await http_client.post(
            "/api/experiments",
            json={
                "name": "baseline",
                "family": "lissajous",
                "search_strategy": "grid",
                "dataset_split": "train",
                "scoring_metric": "procrustes",
                "regularization_weight": 0.0,
                "held_out_accent": "chabad",
                "max_evaluations": 25,
                "rng_seed": 7,
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        run_id = body["run"]["id"]
        assert body["run"]["completed_at"] is not None
        assert body["best_candidate"]["family"] == "lissajous"
        assert body["candidate_count"] == 25

        rows = (await db_session.execute(select(ExperimentRunRow))).scalars().all()
        candidates = (await db_session.execute(select(TransformCandidateRow))).scalars().all()
        assert len(rows) == 1
        assert len(candidates) == 25

        listed = await http_client.get(
            "/api/experiments",
            params={
                "family": "lissajous",
                "strategy": "grid",
                "held_out_accent": "chabad",
                "status": "completed",
            },
        )
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [run_id]

        detail = await http_client.get(f"/api/experiments/{run_id}")
        assert detail.status_code == 200
        assert detail.json()["candidate_count"] == 25


async def test_create_experiment_runs_bayesian_strategy(db_session, db_engine, postgres_url, tmp_path) -> None:
    await _seed_pair(db_session, tmp_path, index=1, frequency_hz=440.0)
    await _seed_pair(db_session, tmp_path, index=2, frequency_hz=660.0)

    async with await _client(db_engine, postgres_url, tmp_path) as http_client:
        response = await http_client.post(
            "/api/experiments",
            json={
                "name": "bayesian-api",
                "family": "lissajous",
                "search_strategy": "bayesian",
                "dataset_split": "train",
                "scoring_metric": "procrustes",
                "regularization_weight": 0.0,
                "max_evaluations": 3,
                "rng_seed": 11,
            },
        )
        listed = await http_client.get("/api/experiments", params={"strategy": "bayesian"})

    assert response.status_code == 201
    body = response.json()
    assert body["run"]["search_strategy"] == "bayesian"
    assert body["run"]["completed_at"] is not None
    assert body["best_candidate"]["family"] == "lissajous"
    assert body["candidate_count"] == 1

    rows = (await db_session.execute(select(ExperimentRunRow))).scalars().all()
    candidates = (await db_session.execute(select(TransformCandidateRow))).scalars().all()
    assert len(rows) == 1
    assert rows[0].search_strategy == "bayesian"
    assert len(candidates) == 1
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [body["run"]["id"]]


async def test_list_experiments_filters_running_status(db_session, db_engine, postgres_url, tmp_path) -> None:
    completed = ExperimentRunRow(
        id=uuid4(),
        name="done",
        family="lissajous",
        search_strategy="grid",
        dataset_split="train",
        scoring_metric="procrustes",
        regularization_weight=0.0,
        held_out_accent=None,
        rng_seed=1,
        font_name="StamAshkenazCLM.ttf",
        config_snapshot={},
        max_evaluations=1,
        started_at=datetime(2026, 4, 16, tzinfo=UTC),
        completed_at=datetime(2026, 4, 16, 0, 0, 1, tzinfo=UTC),
        best_candidate_id=None,
    )
    running = ExperimentRunRow(
        id=uuid4(),
        name="active",
        family="fourier_series",
        search_strategy="grid",
        dataset_split="train",
        scoring_metric="procrustes",
        regularization_weight=0.0,
        held_out_accent="ashkenazi",
        rng_seed=2,
        font_name="StamAshkenazCLM.ttf",
        config_snapshot={},
        max_evaluations=1,
        started_at=datetime(2026, 4, 17, tzinfo=UTC),
        completed_at=None,
        best_candidate_id=None,
    )
    db_session.add_all([completed, running])
    await db_session.commit()

    async with await _client(db_engine, postgres_url, tmp_path) as http_client:
        resp = await http_client.get("/api/experiments", params={"status": "running"})
        unfiltered = await http_client.get("/api/experiments")

    assert resp.status_code == 200
    assert [item["id"] for item in resp.json()] == [str(running.id)]
    assert unfiltered.status_code == 200
    assert {item["id"] for item in unfiltered.json()} == {str(completed.id), str(running.id)}


async def test_get_experiment_handles_missing_tracker_and_candidate(
    db_session, db_engine, postgres_url, tmp_path
) -> None:
    run = ExperimentRunRow(
        id=uuid4(),
        name="ledger-missing",
        family="lissajous",
        search_strategy="grid",
        dataset_split="train",
        scoring_metric="procrustes",
        regularization_weight=0.0,
        held_out_accent=None,
        rng_seed=1,
        font_name="StamAshkenazCLM.ttf",
        config_snapshot={},
        max_evaluations=1,
        started_at=datetime(2026, 4, 16, tzinfo=UTC),
        completed_at=datetime(2026, 4, 16, 0, 0, 1, tzinfo=UTC),
        best_candidate_id=uuid4(),
    )
    no_best = ExperimentRunRow(
        id=uuid4(),
        name="no-best-yet",
        family="lissajous",
        search_strategy="grid",
        dataset_split="train",
        scoring_metric="procrustes",
        regularization_weight=0.0,
        held_out_accent=None,
        rng_seed=2,
        font_name="StamAshkenazCLM.ttf",
        config_snapshot={},
        max_evaluations=1,
        started_at=datetime(2026, 4, 16, tzinfo=UTC),
        completed_at=None,
        best_candidate_id=None,
    )
    db_session.add_all([run, no_best])
    await db_session.commit()

    async with await _client(db_engine, postgres_url, tmp_path) as http_client:
        resp = await http_client.get(f"/api/experiments/{run.id}")
        no_best_resp = await http_client.get(f"/api/experiments/{no_best.id}")

    assert resp.status_code == 200
    assert resp.json()["best_candidate"] is None
    assert resp.json()["candidate_count"] == 0
    assert no_best_resp.status_code == 200
    assert no_best_resp.json()["best_candidate"] is None


async def test_create_experiment_rejects_unknown_family_symbolic_extra_and_empty_dataset(
    db_engine, postgres_url, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing_symbolic_extra() -> None:
        raise experiments.PySRUnavailableError("install [symbolic]")

    monkeypatch.setattr(experiments, "require_symbolic_regressor_factory", missing_symbolic_extra)
    async with await _client(db_engine, postgres_url, tmp_path) as http_client:
        payload = {
            "name": "bad",
            "family": "unknown",
            "search_strategy": "grid",
            "regularization_weight": 0.0,
            "max_evaluations": 1,
            "rng_seed": 1,
        }
        assert (await http_client.post("/api/experiments", json=payload)).status_code == 422
        payload["family"] = "symbolic_regression"
        payload["search_strategy"] = "symbolic-regression"
        symbolic_response = await http_client.post("/api/experiments", json=payload)
        assert symbolic_response.status_code == 422
        assert "install [symbolic]" in symbolic_response.text
        payload["family"] = "lissajous"
        payload["search_strategy"] = "grid"
        assert (await http_client.post("/api/experiments", json=payload)).status_code == 422


async def test_create_experiment_returns_422_for_fit_value_error(
    db_session, db_engine, postgres_url, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _seed_pair(db_session, tmp_path, index=1, frequency_hz=440.0)

    class FailingSearchEngine:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["strategy"] == "grid"

        def fit(self, *args: object, **kwargs: object) -> list[object]:
            raise ValueError("fit failed")

    monkeypatch.setattr(experiments, "SearchEngine", FailingSearchEngine)

    async with await _client(db_engine, postgres_url, tmp_path) as http_client:
        response = await http_client.post(
            "/api/experiments",
            json={
                "name": "fit-error",
                "family": "lissajous",
                "search_strategy": "grid",
                "dataset_split": "train",
                "scoring_metric": "procrustes",
                "regularization_weight": 0.0,
                "max_evaluations": 1,
                "rng_seed": 1,
            },
        )

    assert response.status_code == 422
    assert "fit failed" in response.text


async def test_create_experiment_returns_422_for_late_pysr_unavailable(
    db_session, db_engine, postgres_url, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _seed_pair(db_session, tmp_path, index=1, frequency_hz=440.0)

    class FailingSearchEngine:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["strategy"] == "grid"

        def fit(self, *args: object, **kwargs: object) -> list[object]:
            raise experiments.PySRUnavailableError("late missing symbolic extra")

    monkeypatch.setattr(experiments, "SearchEngine", FailingSearchEngine)

    async with await _client(db_engine, postgres_url, tmp_path) as http_client:
        response = await http_client.post(
            "/api/experiments",
            json={
                "name": "late-pysr-error",
                "family": "lissajous",
                "search_strategy": "grid",
                "dataset_split": "train",
                "scoring_metric": "procrustes",
                "regularization_weight": 0.0,
                "max_evaluations": 1,
                "rng_seed": 1,
            },
        )

    assert response.status_code == 422
    assert "late missing symbolic extra" in response.text


async def test_get_experiment_missing_or_bad_id(db_engine, postgres_url, tmp_path) -> None:
    async with await _client(db_engine, postgres_url, tmp_path) as http_client:
        assert (await http_client.get("/api/experiments/not-a-uuid")).status_code == 404
        assert (await http_client.get(f"/api/experiments/{uuid4()}")).status_code == 404


def test_experiment_create_rejects_unknown_held_out_accent() -> None:
    with pytest.raises(ValidationError, match="held_out_accent"):
        ExperimentCreate(
            name="bad-accent",
            family="lissajous",
            search_strategy="grid",
            regularization_weight=0.0,
            max_evaluations=1,
            held_out_accent="not-an-accent",
            rng_seed=1,
        )


def test_experiment_create_accepts_bayesian_strategy() -> None:
    body = ExperimentCreate(
        name="bayes",
        family="lissajous",
        search_strategy="bayesian",
        regularization_weight=0.0,
        max_evaluations=1,
        rng_seed=1,
    )

    assert body.search_strategy == "bayesian"


def test_config_snapshot_flattens_lists_and_nested_values(postgres_url, tmp_path) -> None:
    class ExtraSettings(BackendSettings):
        nested_value: dict[str, ThetaValue] = Field(default_factory=lambda: {"alpha": 1})

    settings = ExtraSettings(
        database_url=postgres_url,
        audio_dir=tmp_path / "audio",
        contours_dir=tmp_path / "contours",
        font_file=Path("backend/data/fonts/StamAshkenazCLM.ttf"),
        experiments_dir=tmp_path / "experiments",
    )

    snapshot = config_snapshot(settings)

    assert snapshot["search_log_scale_keys"] == "ridge_alpha"
    assert snapshot["nested_value"] == "{'alpha': 1}"
