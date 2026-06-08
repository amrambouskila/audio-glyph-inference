"""Audit Stage-7 recording completeness against the Phase-5 manifest."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import BackendSettings, get_settings
from src.constants import (
    ACCENTS,
    AUDIO_FORM_KEYS,
    BASE_LETTER_BY_GLYPH_FORM,
    GLYPH_FORMS,
    NUM_AUDIO_FORMS,
    NUM_GLYPH_FORMS,
)
from src.data.database import create_engine, session_scope
from src.data.orm.audio_sample_row import AudioSampleRow
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.paired_example_row import PairedExampleRow

_DEFAULT_MANIFEST_PATH = Path("experiments/manifests/phase5_pending_real_data.json")
_DEFAULT_OUTPUT_FORMAT = "text"


@dataclass(frozen=True)
class DatasetAudit:
    """Completeness report for the Stage-7 dataset gate."""

    passed: bool
    expected_audio_samples: int
    audio_sample_count: int
    paired_example_count: int
    glyph_target_count: int
    missing_audio_takes: tuple[str, ...]
    extra_audio_takes: tuple[str, ...]
    unpaired_audio_takes: tuple[str, ...]
    mismatched_pair_takes: tuple[str, ...]
    missing_glyph_forms: tuple[str, ...]


async def audit_stage7_dataset(
    session: AsyncSession,
    settings: BackendSettings,
    manifest_path: Path,
) -> DatasetAudit:
    """Check current DB rows against the constants-backed Stage-7 plan."""
    repetitions = _manifest_repetitions(manifest_path)
    expected_takes = {
        _take_key(accent, letter, pronunciation_variant, repetition)
        for accent in ACCENTS
        for letter, pronunciation_variant in AUDIO_FORM_KEYS
        for repetition in range(1, repetitions + 1)
    }
    audio_takes = await _audio_takes(session, settings.audio_default_speaker_id)
    paired_takes, mismatched_pair_takes = await _paired_audio_takes(session, settings.audio_default_speaker_id)
    glyph_forms = await _glyph_forms(session, settings)

    missing_audio_takes = tuple(sorted(expected_takes - audio_takes))
    extra_audio_takes = tuple(sorted(audio_takes - expected_takes))
    valid_paired_takes = paired_takes - mismatched_pair_takes
    unpaired_audio_takes = tuple(sorted(expected_takes & audio_takes - valid_paired_takes))
    sorted_mismatched_pair_takes = tuple(sorted(mismatched_pair_takes))
    missing_glyph_forms = tuple(glyph_form for glyph_form in GLYPH_FORMS if glyph_form not in glyph_forms)
    passed = not (
        missing_audio_takes
        or extra_audio_takes
        or unpaired_audio_takes
        or sorted_mismatched_pair_takes
        or missing_glyph_forms
    )
    return DatasetAudit(
        passed=passed,
        expected_audio_samples=len(expected_takes),
        audio_sample_count=len(audio_takes),
        paired_example_count=len(paired_takes),
        glyph_target_count=len(glyph_forms),
        missing_audio_takes=missing_audio_takes,
        extra_audio_takes=extra_audio_takes,
        unpaired_audio_takes=unpaired_audio_takes,
        mismatched_pair_takes=sorted_mismatched_pair_takes,
        missing_glyph_forms=missing_glyph_forms,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Stage-7 dataset completeness audit."""
    parser = argparse.ArgumentParser(description="Audit Stage-7 audio/glyph/pair completeness.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST_PATH)
    parser.add_argument("--format", choices=("text", "json"), default=_DEFAULT_OUTPUT_FORMAT)
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.database_url is not None:
        values = settings.model_dump()
        values["database_url"] = args.database_url
        settings = BackendSettings(**values)

    audit = asyncio.run(_audit_with_own_session(settings, args.manifest))
    if args.format == "json":
        print(json.dumps(_audit_payload(audit), sort_keys=True))
    else:
        print(_render_text(audit))
    return 0 if audit.passed else 1


async def _audio_takes(session: AsyncSession, speaker_id: str) -> set[str]:
    stmt = select(
        AudioSampleRow.accent,
        AudioSampleRow.letter,
        AudioSampleRow.pronunciation_variant,
        AudioSampleRow.repetition,
    ).where(AudioSampleRow.speaker_id == speaker_id)
    return {
        _take_key(accent, letter, pronunciation_variant, repetition)
        for accent, letter, pronunciation_variant, repetition in (await session.execute(stmt)).all()
    }


async def _paired_audio_takes(session: AsyncSession, speaker_id: str) -> tuple[set[str], set[str]]:
    stmt = (
        select(
            AudioSampleRow.accent,
            AudioSampleRow.letter,
            AudioSampleRow.pronunciation_variant,
            AudioSampleRow.repetition,
            PairedExampleRow.letter,
            PairedExampleRow.pronunciation_variant,
            GlyphTargetRow.letter,
            GlyphTargetRow.glyph_form,
        )
        .join(PairedExampleRow, PairedExampleRow.audio_sample_id == AudioSampleRow.id)
        .join(GlyphTargetRow, GlyphTargetRow.id == PairedExampleRow.glyph_target_id)
        .where(AudioSampleRow.speaker_id == speaker_id)
    )
    paired_takes: set[str] = set()
    mismatched_takes: set[str] = set()
    for (
        accent,
        audio_letter,
        audio_variant,
        repetition,
        pair_letter,
        pair_variant,
        glyph_letter,
        glyph_form,
    ) in (await session.execute(stmt)).all():
        take = _take_key(accent, audio_letter, audio_variant, repetition)
        paired_takes.add(take)
        glyph_base = BASE_LETTER_BY_GLYPH_FORM.get(glyph_form)
        if (
            pair_letter != audio_letter
            or pair_variant != audio_variant
            or glyph_letter != audio_letter
            or glyph_base != audio_letter
        ):
            mismatched_takes.add(take)
    return paired_takes, mismatched_takes


async def _glyph_forms(session: AsyncSession, settings: BackendSettings) -> set[str]:
    stmt = (
        select(GlyphTargetRow.glyph_form)
        .where(GlyphTargetRow.font_name == settings.font_file.name)
        .where(GlyphTargetRow.raster_size_px == settings.glyph_raster_size_px)
        .group_by(GlyphTargetRow.glyph_form)
    )
    return {glyph_form for (glyph_form,) in (await session.execute(stmt)).all() if glyph_form in GLYPH_FORMS}


async def _audit_with_own_session(settings: BackendSettings, manifest_path: Path) -> DatasetAudit:
    engine = create_engine(settings.database_url)
    try:
        async with session_scope(engine) as session:
            return await audit_stage7_dataset(session, settings, manifest_path)
    finally:
        await engine.dispose()


def _manifest_repetitions(manifest_path: Path) -> int:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest must contain a JSON object")
    data_requirements = manifest.get("data_requirements")
    if not isinstance(data_requirements, dict):
        raise ValueError("manifest data_requirements must be an object")
    repetitions = data_requirements.get("repetitions_per_accent_letter")
    if not isinstance(repetitions, int) or repetitions <= 0:
        raise ValueError("manifest repetitions_per_accent_letter must be a positive integer")
    expected_total = data_requirements.get("total_expected_audio_samples")
    actual_total = len(ACCENTS) * NUM_AUDIO_FORMS * repetitions
    if expected_total != actual_total:
        raise ValueError("manifest total_expected_audio_samples does not match constants")
    return repetitions


def _take_key(accent: str, letter: str, pronunciation_variant: str, repetition: int) -> str:
    return f"{accent}/{letter}/{pronunciation_variant}/{repetition}"


def _audit_payload(audit: DatasetAudit) -> dict[str, object]:
    return {
        "passed": audit.passed,
        "expected_audio_samples": audit.expected_audio_samples,
        "audio_sample_count": audit.audio_sample_count,
        "paired_example_count": audit.paired_example_count,
        "glyph_target_count": audit.glyph_target_count,
        "missing_audio_takes": list(audit.missing_audio_takes),
        "extra_audio_takes": list(audit.extra_audio_takes),
        "unpaired_audio_takes": list(audit.unpaired_audio_takes),
        "mismatched_pair_takes": list(audit.mismatched_pair_takes),
        "missing_glyph_forms": list(audit.missing_glyph_forms),
    }


def _render_text(audit: DatasetAudit) -> str:
    lines = [
        f"Stage-7 dataset audit: {'PASS' if audit.passed else 'FAIL'}",
        f"audio samples: {audit.audio_sample_count}/{audit.expected_audio_samples}",
        f"paired examples: {audit.paired_example_count}/{audit.expected_audio_samples}",
        f"glyph targets: {audit.glyph_target_count}/{NUM_GLYPH_FORMS}",
        _render_issue_line("missing audio takes", audit.missing_audio_takes),
        _render_issue_line("extra audio takes", audit.extra_audio_takes),
        _render_issue_line("unpaired audio takes", audit.unpaired_audio_takes),
        _render_issue_line("mismatched pair takes", audit.mismatched_pair_takes),
        _render_issue_line("missing glyph forms", audit.missing_glyph_forms),
    ]
    return "\n".join(lines)


def _render_issue_line(label: str, values: tuple[str, ...]) -> str:
    if not values:
        return f"{label}: none"
    preview = ", ".join(values[:10])
    suffix = "" if len(values) <= 10 else f", ... (+{len(values) - 10} more)"
    return f"{label}: {preview}{suffix}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
