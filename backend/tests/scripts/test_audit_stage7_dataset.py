"""Tests for scripts/audit_stage7_dataset.py."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from scripts.audit_stage7_dataset import audit_stage7_dataset, main
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import BackendSettings
from src.constants import ACCENTS, AUDIO_FORM_KEYS, BASE_LETTER_BY_GLYPH_FORM, GLYPH_FORMS, NUM_AUDIO_FORMS
from src.data.orm.audio_sample_row import AudioSampleRow
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.paired_example_row import PairedExampleRow


def _settings(postgres_url: str, tmp_path: Path) -> BackendSettings:
    return BackendSettings(
        database_url=postgres_url,
        font_file=tmp_path / "StamAshkenazCLM.ttf",
        contours_dir=tmp_path / "contours",
        experiments_dir=tmp_path / "experiments",
    )


def _manifest(tmp_path: Path, repetitions: int) -> Path:
    path = tmp_path / "manifest.json"
    payload = {
        "data_requirements": {
            "repetitions_per_accent_letter": repetitions,
            "total_expected_audio_samples": len(ACCENTS) * NUM_AUDIO_FORMS * repetitions,
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


async def test_audit_stage7_dataset_reports_missing_rows(
    db_session: AsyncSession,
    postgres_url: str,
    tmp_path: Path,
) -> None:
    settings = _settings(postgres_url, tmp_path)
    manifest = _manifest(tmp_path, repetitions=1)
    await _seed_glyphs(db_session, settings, GLYPH_FORMS[:-1])
    await _seed_audio(
        db_session,
        letter=AUDIO_FORM_KEYS[0][0],
        pronunciation_variant=AUDIO_FORM_KEYS[0][1],
        accent=ACCENTS[0],
        repetition=1,
        paired=True,
    )
    await db_session.commit()

    audit = await audit_stage7_dataset(db_session, settings, manifest)

    assert not audit.passed
    assert audit.expected_audio_samples == len(ACCENTS) * NUM_AUDIO_FORMS
    assert audit.audio_sample_count == 1
    assert audit.paired_example_count == 1
    assert audit.glyph_target_count == len(GLYPH_FORMS) - 1
    assert f"{ACCENTS[0]}/{AUDIO_FORM_KEYS[1][0]}/{AUDIO_FORM_KEYS[1][1]}/1" in audit.missing_audio_takes
    assert audit.missing_glyph_forms == (GLYPH_FORMS[-1],)


async def test_audit_stage7_dataset_passes_complete_minimal_plan(
    db_session: AsyncSession,
    postgres_url: str,
    tmp_path: Path,
) -> None:
    settings = _settings(postgres_url, tmp_path)
    manifest = _manifest(tmp_path, repetitions=1)
    await _seed_glyphs(db_session, settings, GLYPH_FORMS)
    for accent in ACCENTS:
        for letter, pronunciation_variant in AUDIO_FORM_KEYS:
            await _seed_audio(
                db_session,
                letter=letter,
                pronunciation_variant=pronunciation_variant,
                accent=accent,
                repetition=1,
                paired=True,
            )
    await db_session.commit()

    audit = await audit_stage7_dataset(db_session, settings, manifest)

    assert audit.passed
    assert audit.expected_audio_samples == len(ACCENTS) * NUM_AUDIO_FORMS
    assert audit.audio_sample_count == audit.expected_audio_samples
    assert audit.paired_example_count == audit.expected_audio_samples
    assert audit.glyph_target_count == len(GLYPH_FORMS)
    assert audit.missing_audio_takes == ()
    assert audit.extra_audio_takes == ()
    assert audit.unpaired_audio_takes == ()
    assert audit.missing_glyph_forms == ()


async def test_audit_stage7_dataset_reports_extra_and_unpaired_takes(
    db_session: AsyncSession,
    postgres_url: str,
    tmp_path: Path,
) -> None:
    settings = _settings(postgres_url, tmp_path)
    manifest = _manifest(tmp_path, repetitions=1)
    await _seed_audio(
        db_session,
        letter=AUDIO_FORM_KEYS[0][0],
        pronunciation_variant=AUDIO_FORM_KEYS[0][1],
        accent=ACCENTS[0],
        repetition=1,
        paired=False,
    )
    await _seed_audio(
        db_session,
        letter=AUDIO_FORM_KEYS[0][0],
        pronunciation_variant=AUDIO_FORM_KEYS[0][1],
        accent=ACCENTS[0],
        repetition=2,
        paired=False,
    )
    await db_session.commit()

    audit = await audit_stage7_dataset(db_session, settings, manifest)

    assert not audit.passed
    assert f"{ACCENTS[0]}/{AUDIO_FORM_KEYS[0][0]}/{AUDIO_FORM_KEYS[0][1]}/1" in audit.unpaired_audio_takes
    assert audit.extra_audio_takes == (f"{ACCENTS[0]}/{AUDIO_FORM_KEYS[0][0]}/{AUDIO_FORM_KEYS[0][1]}/2",)


async def test_audit_stage7_dataset_reports_mismatched_pairs(
    db_session: AsyncSession,
    postgres_url: str,
    tmp_path: Path,
) -> None:
    settings = _settings(postgres_url, tmp_path)
    manifest = _manifest(tmp_path, repetitions=1)
    await _seed_mismatched_pair(db_session, audio_letter=AUDIO_FORM_KEYS[0][0], glyph_letter=AUDIO_FORM_KEYS[1][0])
    await db_session.commit()

    audit = await audit_stage7_dataset(db_session, settings, manifest)

    expected_take = f"{ACCENTS[0]}/{AUDIO_FORM_KEYS[0][0]}/{AUDIO_FORM_KEYS[0][1]}/1"
    assert not audit.passed
    assert audit.paired_example_count == 1
    assert audit.mismatched_pair_takes == (expected_take,)
    assert expected_take in audit.unpaired_audio_takes


def test_main_prints_json_and_returns_failure(
    postgres_url: str,
    db_engine,
    tmp_path: Path,
    capsys,
) -> None:
    assert db_engine is not None
    manifest = _manifest(tmp_path, repetitions=1)

    result = main(["--database-url", postgres_url, "--manifest", str(manifest), "--format", "json"])

    assert result == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is False
    assert payload["expected_audio_samples"] == len(ACCENTS) * NUM_AUDIO_FORMS
    assert payload["mismatched_pair_takes"] == []


def test_main_prints_text(
    postgres_url: str,
    db_engine,
    tmp_path: Path,
    capsys,
) -> None:
    assert db_engine is not None
    manifest = _manifest(tmp_path, repetitions=1)

    result = main(["--database-url", postgres_url, "--manifest", str(manifest)])

    assert result == 1
    output = capsys.readouterr().out
    assert "Stage-7 dataset audit: FAIL" in output
    assert "audio samples: 0/" in output
    assert "mismatched pair takes: none" in output


def test_invalid_manifest_rejected(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"data_requirements": {"repetitions_per_accent_letter": 1}}), encoding="utf-8")

    try:
        main(["--database-url", "postgresql+asyncpg://user:pass@localhost/db", "--manifest", str(manifest)])
    except ValueError as exc:
        assert "total_expected_audio_samples" in str(exc)
    else:
        raise AssertionError("invalid manifest should fail before database connection")


async def _seed_glyphs(db_session: AsyncSession, settings: BackendSettings, glyph_forms: tuple[str, ...]) -> None:
    for glyph_form in glyph_forms:
        db_session.add(
            GlyphTargetRow(
                id=uuid4(),
                letter=BASE_LETTER_BY_GLYPH_FORM[glyph_form],
                glyph_form=glyph_form,
                font_name=settings.font_file.name,
                raster_size_px=settings.glyph_raster_size_px,
                contour_path=f"/app/data/contours/{glyph_form}.npz",
                num_points=settings.glyph_contour_num_points,
                num_contours=1,
            )
        )


async def _seed_audio(
    db_session: AsyncSession,
    *,
    letter: str,
    pronunciation_variant: str,
    accent: str,
    repetition: int,
    paired: bool,
) -> None:
    audio = AudioSampleRow(
        id=uuid4(),
        letter=letter,
        speaker_id="owner",
        accent=accent,
        repetition=repetition,
        pronunciation_variant=pronunciation_variant,
        source="user",
        file_path=f"/app/data/audio/{accent}/{letter}/sample-rep{repetition}.m4a",
        sample_rate_hz=44_100,
        duration_s=1.2,
        recorded_at=datetime(2026, 4, 16, tzinfo=UTC),
    )
    db_session.add(audio)
    if paired:
        glyph = GlyphTargetRow(
            id=uuid4(),
            letter=letter,
            glyph_form=letter,
            font_name="StamAshkenazCLM.ttf",
            raster_size_px=256,
            contour_path=f"/app/data/contours/{letter}.npz",
            num_points=256,
            num_contours=1,
        )
        db_session.add(glyph)
        await db_session.flush()
        db_session.add(
            PairedExampleRow(
                id=uuid4(),
                audio_sample_id=audio.id,
                glyph_target_id=glyph.id,
                letter=letter,
                pronunciation_variant=pronunciation_variant,
                glyph_form=letter,
                split="train",
            )
        )


async def _seed_mismatched_pair(db_session: AsyncSession, *, audio_letter: str, glyph_letter: str) -> None:
    audio = AudioSampleRow(
        id=uuid4(),
        letter=audio_letter,
        speaker_id="owner",
        accent=ACCENTS[0],
        repetition=1,
        pronunciation_variant=AUDIO_FORM_KEYS[0][1],
        source="user",
        file_path=f"/app/data/audio/{ACCENTS[0]}/{audio_letter}/sample-rep1.m4a",
        sample_rate_hz=44_100,
        duration_s=1.2,
        recorded_at=datetime(2026, 4, 16, tzinfo=UTC),
    )
    glyph = GlyphTargetRow(
        id=uuid4(),
        letter=glyph_letter,
        glyph_form=glyph_letter,
        font_name="StamAshkenazCLM.ttf",
        raster_size_px=256,
        contour_path=f"/app/data/contours/{glyph_letter}.npz",
        num_points=256,
        num_contours=1,
    )
    db_session.add_all([audio, glyph])
    await db_session.flush()
    db_session.add(
        PairedExampleRow(
            id=uuid4(),
            audio_sample_id=audio.id,
            glyph_target_id=glyph.id,
            letter=audio_letter,
            pronunciation_variant=AUDIO_FORM_KEYS[0][1],
            glyph_form=glyph_letter,
            split="train",
        )
    )
