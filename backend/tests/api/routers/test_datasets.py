"""Integration tests for src/api/routers/datasets.py — real app + real Postgres.

Pairs/list cases seed rows directly through the session. The audio upload cases
use a soundfile-decodable synthetic payload so `uv run pytest` does not require
a host ffmpeg binary; the committed .m4a fixture is covered in the preprocessor
decode smoke test when ffmpeg is available.
"""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

import numpy as np
import soundfile as sf
from httpx import ASGITransport, AsyncClient
from src.api.main import create_app
from src.constants import HEBREW_LETTERS, PRONUNCIATION_VARIANTS_BY_BASE_LETTER
from src.data.orm.audio_sample_row import AudioSampleRow
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.paired_example_row import PairedExampleRow

from tests.conftest import build_settings

SR = 44_100


def _upload_payload() -> bytes:
    pad = np.zeros(int(SR * 0.5), dtype=np.float64)
    t = np.linspace(0.0, 1.0, SR, endpoint=False)
    tone = 0.3 * np.sin(2.0 * np.pi * 440.0 * t)
    audio = np.concatenate([pad, tone, pad])
    output = BytesIO()
    sf.write(output, audio, SR, format="WAV")
    return output.getvalue()


def _upload(client, *, letter="א", accent="ashkenazi", repetition=1, content_type="audio/mp4", data=None):
    payload = _upload_payload() if data is None else data
    return client.post(
        "/api/datasets/audio",
        data={"letter": letter, "accent": accent, "repetition": str(repetition)},
        files={"file": ("test-sample.m4a", payload, content_type)},
    )


def _audio_row(letter="א", accent="ashkenazi", repetition=1) -> AudioSampleRow:
    resolved_variant = PRONUNCIATION_VARIANTS_BY_BASE_LETTER[letter][0]
    return AudioSampleRow(
        id=uuid4(),
        letter=letter,
        speaker_id="owner",
        accent=accent,
        repetition=repetition,
        pronunciation_variant=resolved_variant,
        source="user",
        file_path=f"/x/{letter}-{repetition}.m4a",
        sample_rate_hz=44_100,
        duration_s=1.0,
        recorded_at=datetime(2026, 4, 16, 12, 0, 0, tzinfo=UTC),
    )


def _glyph_row(letter="א") -> GlyphTargetRow:
    return GlyphTargetRow(
        id=uuid4(),
        letter=letter,
        glyph_form=letter,
        font_name="StamAshkenazCLM.ttf",
        raster_size_px=256,
        contour_path=f"/c/{letter}.npz",
        num_points=256,
        num_contours=1,
    )


async def _seed_pair(db_session, *, letter="א", accent="ashkenazi", split="train", repetition=1) -> PairedExampleRow:
    audio = _audio_row(letter=letter, accent=accent, repetition=repetition)
    glyph = _glyph_row(letter=letter)
    db_session.add_all([audio, glyph])
    await db_session.flush()
    pair = PairedExampleRow(
        id=uuid4(),
        audio_sample_id=audio.id,
        glyph_target_id=glyph.id,
        letter=letter,
        pronunciation_variant=audio.pronunciation_variant,
        glyph_form=letter,
        split=split,
    )
    db_session.add(pair)
    await db_session.commit()
    return pair


# --- POST /api/datasets/audio ---


async def test_upload_audio_happy(client) -> None:
    resp = await _upload(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["letter"] == "א"
    assert body["accent"] == "ashkenazi"
    assert body["repetition"] == 1
    assert body["pronunciation_variant"] == "plain"
    assert body["source"] == "user"
    assert body["sample_rate_hz"] == 44_100
    assert body["file_path"].endswith(".m4a")


async def test_upload_audio_unknown_letter(client) -> None:
    assert (await _upload(client, letter="Q")).status_code == 422


async def test_upload_audio_unknown_accent(client) -> None:
    assert (await _upload(client, accent="klingon")).status_code == 422


async def test_upload_audio_hard_soft_variant(client) -> None:
    resp = await client.post(
        "/api/datasets/audio",
        data={"letter": "ב", "accent": "ashkenazi", "repetition": "1", "pronunciation_variant": "hard"},
        files={"file": ("test-sample.m4a", _upload_payload(), "audio/mp4")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["letter"] == "ב"
    assert body["pronunciation_variant"] == "hard"
    assert "/hard/" in body["file_path"].replace("\\", "/")


async def test_upload_audio_invalid_variant_for_letter(client) -> None:
    resp = await client.post(
        "/api/datasets/audio",
        data={"letter": "א", "accent": "ashkenazi", "repetition": "1", "pronunciation_variant": "hard"},
        files={"file": ("test-sample.m4a", _upload_payload(), "audio/mp4")},
    )
    assert resp.status_code == 422


async def test_upload_audio_bad_repetition(client) -> None:
    assert (await _upload(client, repetition=0)).status_code == 422


async def test_upload_audio_unsupported_media_type(client) -> None:
    assert (await _upload(client, content_type="text/plain")).status_code == 415


async def test_upload_audio_too_large(db_engine, postgres_url, tmp_path) -> None:
    settings = build_settings(postgres_url, tmp_path, audio_max_upload_bytes=10)
    app = create_app(settings=settings, engine=db_engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await _upload(c)).status_code == 413


async def test_upload_audio_validation_rejected(db_engine, postgres_url, tmp_path) -> None:
    settings = build_settings(postgres_url, tmp_path, audio_active_speech_max_s=0.1)
    app = create_app(settings=settings, engine=db_engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await _upload(c)).status_code == 422


async def test_upload_audio_duplicate_take_conflict(client) -> None:
    assert (await _upload(client)).status_code == 201
    assert (await _upload(client)).status_code == 409


# --- POST /api/datasets/glyphs ---


async def test_render_glyph_happy(client) -> None:
    resp = await client.post("/api/datasets/glyphs", params={"letter": "א"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["letter"] == "א"
    assert body["glyph_form"] == body["letter"]
    assert body["num_contours"] == 1
    assert body["contour_path"].endswith(".npz")


async def test_render_glyph_detached_stroke_has_two_contours(client) -> None:
    resp = await client.post("/api/datasets/glyphs", params={"letter": "ה"})
    assert resp.status_code == 201
    assert resp.json()["num_contours"] == 2


async def test_render_glyph_sofit_form(client) -> None:
    resp = await client.post("/api/datasets/glyphs", params={"letter": "כ", "glyph_form": "ך"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["letter"] == "כ"
    assert body["glyph_form"] == "ך"
    assert body["contour_path"].endswith(".npz")


async def test_render_glyph_rejects_mismatched_sofit_form(client) -> None:
    resp = await client.post("/api/datasets/glyphs", params={"letter": "ב", "glyph_form": "ך"})
    assert resp.status_code == 422


async def test_render_glyph_unknown_glyph_form(client) -> None:
    resp = await client.post("/api/datasets/glyphs", params={"letter": "א", "glyph_form": "Q"})
    assert resp.status_code == 422


async def test_render_glyph_unknown_letter(client) -> None:
    assert (await client.post("/api/datasets/glyphs", params={"letter": "Q"})).status_code == 422


# --- GET /api/datasets/glyphs ---


async def test_list_glyphs_no_filter(client, db_session) -> None:
    first = _glyph_row(letter=HEBREW_LETTERS[1])
    second = _glyph_row(letter=HEBREW_LETTERS[0])
    db_session.add_all([first, second])
    await db_session.commit()
    resp = await client.get("/api/datasets/glyphs")
    assert resp.status_code == 200
    assert [item["letter"] for item in resp.json()] == [HEBREW_LETTERS[0], HEBREW_LETTERS[1]]


async def test_list_glyphs_filter_letter_and_reject_unknown(client, db_session) -> None:
    db_session.add_all([_glyph_row(letter=HEBREW_LETTERS[0]), _glyph_row(letter=HEBREW_LETTERS[1])])
    await db_session.commit()
    resp = await client.get("/api/datasets/glyphs", params={"letter": HEBREW_LETTERS[1]})
    assert resp.status_code == 200
    assert [item["letter"] for item in resp.json()] == [HEBREW_LETTERS[1]]
    assert (await client.get("/api/datasets/glyphs", params={"letter": "Q"})).status_code == 422


async def test_list_glyphs_filter_glyph_form(client, db_session) -> None:
    db_session.add_all([_glyph_row(letter="כ"), _glyph_row(letter="א")])
    await db_session.commit()
    resp = await client.get("/api/datasets/glyphs", params={"glyph_form": "כ"})
    assert resp.status_code == 200
    assert [item["glyph_form"] for item in resp.json()] == ["כ"]
    assert (await client.get("/api/datasets/glyphs", params={"glyph_form": "Q"})).status_code == 422


# --- POST /api/datasets/pairs ---


async def test_create_pair_happy(client, db_session) -> None:
    audio, glyph = _audio_row(letter="ג"), _glyph_row(letter="ג")
    db_session.add_all([audio, glyph])
    await db_session.commit()
    resp = await client.post(
        "/api/datasets/pairs",
        json={"audio_sample_id": str(audio.id), "glyph_target_id": str(glyph.id), "split": "train"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["letter"] == "ג"
    assert body["pronunciation_variant"] == audio.pronunciation_variant
    assert body["glyph_form"] == glyph.glyph_form
    assert body["split"] == "train"


async def test_create_pair_not_found(client) -> None:
    resp = await client.post(
        "/api/datasets/pairs",
        json={"audio_sample_id": str(uuid4()), "glyph_target_id": str(uuid4()), "split": "train"},
    )
    assert resp.status_code == 404


async def test_create_pair_letter_mismatch(client, db_session) -> None:
    audio, glyph = _audio_row(letter="ג"), _glyph_row(letter="ב")
    db_session.add_all([audio, glyph])
    await db_session.commit()
    resp = await client.post(
        "/api/datasets/pairs",
        json={"audio_sample_id": str(audio.id), "glyph_target_id": str(glyph.id), "split": "train"},
    )
    assert resp.status_code == 422


# --- GET /api/datasets/pairs ---


async def test_list_pairs_no_filter(client, db_session) -> None:
    await _seed_pair(db_session, split="train", repetition=1)
    await _seed_pair(db_session, split="val", repetition=2)
    resp = await client.get("/api/datasets/pairs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_pairs_filter_split(client, db_session) -> None:
    await _seed_pair(db_session, split="train", repetition=1)
    await _seed_pair(db_session, split="test", repetition=2)
    resp = await client.get("/api/datasets/pairs", params={"split": "test"})
    assert [p["split"] for p in resp.json()] == ["test"]


async def test_list_pairs_filter_letter(client, db_session) -> None:
    await _seed_pair(db_session, letter="א", repetition=1)
    await _seed_pair(db_session, letter="ב", repetition=2)
    resp = await client.get("/api/datasets/pairs", params={"letter": "ב"})
    assert [p["letter"] for p in resp.json()] == ["ב"]


async def test_list_pairs_filter_pronunciation_variant_and_glyph_form(client, db_session) -> None:
    await _seed_pair(db_session, letter="ב", repetition=1)
    await _seed_pair(db_session, letter="א", repetition=2)
    variant_resp = await client.get("/api/datasets/pairs", params={"pronunciation_variant": "hard"})
    assert [p["letter"] for p in variant_resp.json()] == ["ב"]
    glyph_resp = await client.get("/api/datasets/pairs", params={"glyph_form": "א"})
    assert [p["glyph_form"] for p in glyph_resp.json()] == ["א"]


async def test_list_pairs_filter_accent(client, db_session) -> None:
    await _seed_pair(db_session, accent="ashkenazi", repetition=1)
    await _seed_pair(db_session, accent="yemenite", repetition=2)
    resp = await client.get("/api/datasets/pairs", params={"accent": "yemenite"})
    assert len(resp.json()) == 1
