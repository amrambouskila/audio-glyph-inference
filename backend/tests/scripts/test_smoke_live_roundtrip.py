"""Tests for scripts/smoke_live_roundtrip.py."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import msgpack
import numpy as np
import pytest
import scripts.smoke_live_roundtrip as smoke
from scripts.seed_live_smoke import seed_live_smoke_data
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import BackendSettings
from src.constants import GLYPH_FORMS, NUM_GLYPH_FORMS
from src.data.orm.experiment_run_row import ExperimentRunRow
from src.simulation.experiment_tracker import ExperimentTracker
from tests.conftest import FONT_PATH


def _settings(postgres_url: str, tmp_path: Path) -> BackendSettings:
    return BackendSettings(
        database_url=postgres_url,
        font_file=FONT_PATH,
        contours_dir=tmp_path / "contours",
        experiments_dir=tmp_path / "experiments",
    )


async def test_smoke_live_roundtrip_selects_latest_candidate_and_all_glyphs(
    db_session: AsyncSession,
    postgres_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(postgres_url, tmp_path)
    _, old_run, _ = await seed_live_smoke_data(db_session, settings, ExperimentTracker(settings.experiments_dir))
    _, new_run, _ = await seed_live_smoke_data(db_session, settings, ExperimentTracker(settings.experiments_dir))
    old_run_row = await db_session.get(ExperimentRunRow, old_run.id)
    assert old_run_row is not None
    old_run_row.started_at = datetime(2026, 1, 1, tzinfo=UTC)
    new_run_row = await db_session.get(ExperimentRunRow, new_run.id)
    assert new_run_row is not None
    new_run_row.started_at = datetime(2026, 1, 2, tzinfo=UTC)
    await db_session.commit()

    seen_candidate_ids = []
    seen_targets = []

    async def fake_roundtrip_glyph(
        websocket_url: str,
        candidate_id,
        target: smoke.LiveSmokeTarget,
        settings: BackendSettings,
        pcm16: bytes,
    ) -> smoke.LiveSmokeResult:
        # Test fixture URL, never dialled: the smoke helper is driven against a stub here.
        # nosemgrep: javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket
        assert websocket_url == "ws://test/ws/live"
        expected_samples = (
            settings.audio_frame_length_samples + (settings.feature_n_segments - 1) * settings.audio_hop_length_samples
        )
        assert len(pcm16) == expected_samples * 2
        seen_candidate_ids.append(candidate_id)
        seen_targets.append(target)
        return smoke.LiveSmokeResult(
            letter=target.letter,
            glyph_form=target.glyph_form,
            glyph_target_id=target.glyph_target_id,
            shape_distance=0.5,
            generated_points=settings.glyph_contour_num_points,
            target_points=settings.glyph_contour_num_points,
        )

    monkeypatch.setattr(smoke, "_roundtrip_glyph", fake_roundtrip_glyph)

    # Test fixture URL, never dialled: the smoke helper is driven against a stub here.
    # nosemgrep: javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket
    results = await smoke.smoke_live_roundtrip(db_session, settings, "ws://test/ws/live", None)

    assert len(results) == NUM_GLYPH_FORMS
    assert [result.glyph_form for result in results] == list(GLYPH_FORMS)
    assert set(seen_candidate_ids) == {new_run.best_candidate_id}
    assert [target.glyph_form for target in seen_targets] == list(GLYPH_FORMS)


async def test_glyph_targets_reports_missing_letters(
    db_session: AsyncSession,
    postgres_url: str,
    tmp_path: Path,
) -> None:
    settings = _settings(postgres_url, tmp_path)

    with pytest.raises(RuntimeError, match="missing glyph targets"):
        await smoke._glyph_targets(db_session, settings)


async def test_latest_completed_candidate_requires_completed_run(db_session: AsyncSession) -> None:
    with pytest.raises(RuntimeError, match="no completed experiment run"):
        await smoke._latest_completed_candidate_id(db_session)


def test_message_helpers_and_synthetic_pcm16() -> None:
    payload = {"type": "configured", "candidate_id": str(uuid4()), "glyph_target_id": str(uuid4())}
    assert smoke._unpack_message(smoke._pack_message(payload)) == payload
    assert len(smoke._synthetic_pcm16(16_000, 128, 32, 3)) == 384
    with pytest.raises(RuntimeError, match="binary MessagePack"):
        smoke._unpack_message("text")
    with pytest.raises(RuntimeError, match="MessagePack map"):
        smoke._unpack_message(msgpack.packb(["bad"], use_bin_type=True))


def test_validate_score_accepts_and_rejects_score_payloads() -> None:
    target = smoke.LiveSmokeTarget(letter="alef", glyph_form="alef", glyph_target_id=uuid4())
    result = smoke._validate_score(
        target,
        {
            "type": "score",
            "shape_distance": 0.25,
            "contours": [[0.0, 0.0]],
            "target_contours": [[0.0, 0.0]],
        },
    )
    assert result.shape_distance == 0.25
    assert result.generated_points == 1
    assert result.target_points == 1

    with pytest.raises(RuntimeError, match="expected score"):
        smoke._validate_score(target, {"type": "error", "message": "x"})
    with pytest.raises(RuntimeError, match="finite float"):
        smoke._validate_score(
            target,
            {"type": "score", "shape_distance": np.nan, "contours": [], "target_contours": []},
        )
    with pytest.raises(RuntimeError, match="contour lists"):
        smoke._validate_score(target, {"type": "score", "shape_distance": 0.1, "contours": "bad"})
    with pytest.raises(RuntimeError, match="non-empty"):
        smoke._validate_score(target, {"type": "score", "shape_distance": 0.1, "contours": [], "target_contours": []})


def test_main_prints_summary(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    glyph_target_id = uuid4()

    async def fake_smoke_with_own_session(
        settings: BackendSettings,
        websocket_url: str,
        candidate_id,
    ) -> list[smoke.LiveSmokeResult]:
        # Test fixture URL, never dialled: the smoke helper is driven against a stub here.
        # nosemgrep: javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket
        assert websocket_url == "ws://test/ws/live"
        return [
            smoke.LiveSmokeResult(
                letter="alef",
                glyph_form="alef",
                glyph_target_id=glyph_target_id,
                shape_distance=0.125,
                generated_points=settings.glyph_contour_num_points,
                target_points=settings.glyph_contour_num_points,
            )
        ]

    monkeypatch.setattr(smoke, "_smoke_with_own_session", fake_smoke_with_own_session)

    # Test fixture URL, never dialled: the smoke helper is driven against a stub here.
    # nosemgrep: javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket
    result = smoke.main(["--websocket-url", "ws://test/ws/live", "--font-file", str(FONT_PATH)])

    assert result == 0
    output = capsys.readouterr().out
    assert "alef: d=0.125000" in output
    assert "Live round-trip smoke passed for 1 glyph targets." in output
