"""Tests for src/api/routers/live.py."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import msgpack
import numpy as np
import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from src.api.main import create_app
from src.api.routers.live import (
    _audio_frames,
    _configure,
    _metric_field,
    _receive_payload,
    _score_payload,
    _unpack_message,
    _uuid_field,
)
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.transform_candidate_row import TransformCandidateRow
from src.simulation.contour_io import save_contours

from tests.conftest import build_settings

N_POINTS = 256


class FakeWebSocket:
    def __init__(self, message: object) -> None:
        self._message = message

    async def receive(self) -> object:
        return self._message


def _ellipse() -> np.ndarray:
    t = 2.0 * np.pi * np.arange(N_POINTS, dtype=np.float64) / N_POINTS
    return np.stack([0.5 * np.cos(t), 0.25 * np.sin(t)], axis=1).astype(np.float64)


def _pcm16() -> bytes:
    t = np.arange(16_000, dtype=np.float64) / 16_000.0
    samples = (0.2 * np.sin(2.0 * np.pi * 440.0 * t) * 32767.0).astype("<i2")
    return samples.tobytes()


def _pack(payload: dict[str, object]) -> bytes:
    return msgpack.packb(payload, use_bin_type=True)


def _unpack(data: bytes) -> dict[str, object]:
    value = msgpack.unpackb(data, raw=False)
    assert isinstance(value, dict)
    return {str(key): item for key, item in value.items()}


async def _seed_live_rows(db_session, tmp_path: Path, contour: np.ndarray | None = None) -> tuple[str, str]:
    contour_path = tmp_path / "target.npz"
    save_contours(contour_path, [_ellipse() if contour is None else contour])
    glyph_id = uuid4()
    candidate_id = uuid4()
    db_session.add(
        GlyphTargetRow(
            id=glyph_id,
            letter="alef",
            glyph_form="alef",
            font_name="StamAshkenazCLM.ttf",
            raster_size_px=256,
            contour_path=str(contour_path),
            num_points=N_POINTS,
            num_contours=1,
        )
    )
    db_session.add(
        TransformCandidateRow(
            id=candidate_id,
            family="lissajous",
            theta={
                "freq_ratio_a": 1,
                "freq_ratio_b": 1,
                "affine_w": [0.0] * 72,
                "affine_b": [0.0, 1.0, 0.5],
            },
            expression=None,
            shared_across_letters=True,
            interpretability_score=0.8,
            simplicity_score=0.7,
            mean_shape_distance=0.1,
            lookup_ratio=0.2,
            created_at=datetime(2026, 4, 16, tzinfo=UTC),
        )
    )
    await db_session.commit()
    return str(candidate_id), str(glyph_id)


async def test_live_websocket_configures_and_scores_audio(db_session, db_engine, postgres_url, tmp_path) -> None:
    candidate_id, glyph_id = await _seed_live_rows(db_session, tmp_path)
    app = create_app(settings=build_settings(postgres_url, tmp_path))

    with TestClient(app) as client, client.websocket_connect("/ws/live") as websocket:
        websocket.send_bytes(
            _pack(
                {
                    "type": "configure",
                    "candidate_id": candidate_id,
                    "glyph_target_id": glyph_id,
                    "scoring_metric": "procrustes",
                }
            )
        )
        assert _unpack(websocket.receive_bytes()) == {
            "type": "configured",
            "candidate_id": candidate_id,
            "glyph_target_id": glyph_id,
        }

        websocket.send_bytes(_pack({"type": "audio", "sample_rate_hz": 16_000, "pcm16": _pcm16()}))
        score = _unpack(websocket.receive_bytes())

        websocket.send_bytes(_pack({"type": "audio", "sample_rate_hz": 8_000, "pcm16": _pcm16()}))
        error = _unpack(websocket.receive_bytes())

    assert score["type"] == "score"
    assert isinstance(score["shape_distance"], float)
    assert len(score["contours"]) == N_POINTS
    assert len(score["target_contours"]) == N_POINTS
    assert error["message"] == "live audio sample_rate_hz must match backend audio_sample_rate_hz"


async def test_live_websocket_reports_protocol_errors(db_engine, postgres_url, tmp_path) -> None:
    app = create_app(settings=build_settings(postgres_url, tmp_path))

    with TestClient(app) as client, client.websocket_connect("/ws/live") as websocket:
        websocket.send_bytes(b"\xc1")
        assert _unpack(websocket.receive_bytes())["message"] == "live message must be valid MessagePack"

        websocket.send_text("not binary")
        assert _unpack(websocket.receive_bytes())["message"] == "live message must be binary MessagePack"

        websocket.send_bytes(_pack(["not", "a", "map"]))
        assert _unpack(websocket.receive_bytes())["message"] == "live message must be a MessagePack map"

        websocket.send_bytes(msgpack.packb({1: "audio"}, use_bin_type=True))
        assert _unpack(websocket.receive_bytes())["message"] == "live message keys must be strings"

        websocket.send_bytes(_pack({"type": "audio", "sample_rate_hz": 16_000, "pcm16": _pcm16()}))
        assert _unpack(websocket.receive_bytes())["message"] == "send configure before audio"

        websocket.send_bytes(_pack({"type": "unknown"}))
        assert _unpack(websocket.receive_bytes())["message"] == "unknown message type"

        websocket.send_bytes(
            _pack({"type": "configure", "candidate_id": "not-a-uuid", "glyph_target_id": str(uuid4())})
        )
        assert _unpack(websocket.receive_bytes())["message"] == "candidate_id must be a UUID string"

        websocket.send_bytes(
            _pack(
                {
                    "type": "configure",
                    "candidate_id": str(uuid4()),
                    "glyph_target_id": str(uuid4()),
                }
            )
        )
        assert _unpack(websocket.receive_bytes())["message"] == "candidate_id not found"


async def test_live_websocket_reports_scoring_errors(db_session, db_engine, postgres_url, tmp_path) -> None:
    bad_target = _ellipse()
    bad_target[0, 0] = np.nan
    candidate_id, glyph_id = await _seed_live_rows(db_session, tmp_path, bad_target)
    app = create_app(settings=build_settings(postgres_url, tmp_path))

    with TestClient(app) as client, client.websocket_connect("/ws/live") as websocket:
        websocket.send_bytes(
            _pack(
                {
                    "type": "configure",
                    "candidate_id": candidate_id,
                    "glyph_target_id": glyph_id,
                    "scoring_metric": "chamfer",
                }
            )
        )
        assert _unpack(websocket.receive_bytes()) == {
            "type": "configured",
            "candidate_id": candidate_id,
            "glyph_target_id": glyph_id,
        }

        websocket.send_bytes(_pack({"type": "audio", "sample_rate_hz": 16_000, "pcm16": _pcm16()}))
        error = _unpack(websocket.receive_bytes())

    assert error["type"] == "error"
    assert "finite" in str(error["message"])


async def test_configure_reports_missing_glyph(db_session, tmp_path) -> None:
    candidate_id, _ = await _seed_live_rows(db_session, tmp_path)
    with pytest.raises(ValueError, match="glyph_target_id not found"):
        await _configure(
            {
                "candidate_id": candidate_id,
                "glyph_target_id": str(uuid4()),
            },
            db_session,
        )


def test_live_message_helper_validation() -> None:
    valid_uuid = str(uuid4())
    contour = _ellipse()
    score_payload = _score_payload(contour, contour, 0.25)
    assert score_payload["type"] == "score"
    assert score_payload["shape_distance"] == 0.25
    assert len(score_payload["contours"]) == N_POINTS
    assert len(score_payload["target_contours"]) == N_POINTS
    assert _uuid_field({"candidate_id": valid_uuid}, "candidate_id") == uuid4().__class__(valid_uuid)
    assert _metric_field({}) == "procrustes"
    with pytest.raises(ValueError, match="shape_distance"):
        _score_payload(contour, contour, np.nan)
    with pytest.raises(ValueError, match="generated contour.*shape"):
        _score_payload(contour[:, 0], contour, 0.25)
    with pytest.raises(ValueError, match="target contour.*shape"):
        _score_payload(contour, contour[:, 0], 0.25)
    bad_generated = contour.copy()
    bad_generated[0, 0] = np.inf
    with pytest.raises(ValueError, match="generated contour coordinates"):
        _score_payload(bad_generated, contour, 0.25)
    bad_target = contour.copy()
    bad_target[0, 0] = np.inf
    with pytest.raises(ValueError, match="target contour coordinates"):
        _score_payload(contour, bad_target, 0.25)
    with pytest.raises(ValueError, match="UUID"):
        _uuid_field({"candidate_id": 1}, "candidate_id")
    with pytest.raises(ValueError, match="UUID"):
        _uuid_field({"candidate_id": "not-a-uuid"}, "candidate_id")
    with pytest.raises(ValueError, match="scoring_metric"):
        _metric_field({"scoring_metric": "bad"})
    with pytest.raises(ValueError, match="MessagePack map"):
        _unpack_message(_pack(["bad"]))
    with pytest.raises(ValueError, match="valid MessagePack"):
        _unpack_message(b"\xc1")
    with pytest.raises(ValueError, match="keys must be strings"):
        _unpack_message(msgpack.packb({1: "bad"}, use_bin_type=True))


async def test_receive_payload_validates_websocket_events() -> None:
    payload = await _receive_payload(FakeWebSocket({"bytes": _pack({"type": "unknown"})}))
    assert payload == {"type": "unknown"}
    with pytest.raises(ValueError, match="WebSocket event"):
        await _receive_payload(FakeWebSocket("bad"))
    with pytest.raises(ValueError, match="binary MessagePack"):
        await _receive_payload(FakeWebSocket({"text": "bad"}))
    with pytest.raises(WebSocketDisconnect):
        await _receive_payload(FakeWebSocket({"type": "websocket.disconnect"}))


def test_audio_frames_validate_and_pad_pcm16() -> None:
    frames = _audio_frames(
        {"sample_rate_hz": 16_000, "pcm16": np.array([0, 32767], dtype="<i2").tobytes()},
        expected_sample_rate_hz=16_000,
        frame_length_samples=4,
        hop_length_samples=2,
    )
    assert frames.shape == (1, 4)
    np.testing.assert_allclose(frames[0, :2], [0.0, 32767.0 / 32768.0], atol=1e-12)
    with pytest.raises(ValueError, match="sample_rate_hz"):
        _audio_frames(
            {"sample_rate_hz": 8_000, "pcm16": b""},
            expected_sample_rate_hz=16_000,
            frame_length_samples=4,
            hop_length_samples=2,
        )
    with pytest.raises(ValueError, match="pcm16"):
        _audio_frames(
            {"sample_rate_hz": 16_000, "pcm16": "not-bytes"},
            expected_sample_rate_hz=16_000,
            frame_length_samples=4,
            hop_length_samples=2,
        )
