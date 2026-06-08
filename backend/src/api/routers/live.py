"""WebSocket live-pronunciation router using MessagePack binary frames."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from uuid import UUID

import msgpack
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.score_payload import validated_score_payload
from src.data.database import create_session_factory
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.transform_candidate_row import TransformCandidateRow
from src.models.transform_candidate import TransformCandidate
from src.simulation.contour_compare import contour_compare
from src.simulation.contour_io import load_contours
from src.simulation.transforms.family_registry import build_family
from src.simulation.transforms.transform_base import TransformFamily

router = APIRouter(tags=["live"])

_METRICS = frozenset({"procrustes", "frechet", "chamfer"})


@router.websocket("/ws/live")
async def live_pronunciation(websocket: WebSocket) -> None:
    """Receive MessagePack audio frames and stream generated geometry scores."""
    await websocket.accept()
    settings = websocket.app.state.settings
    session_factory = create_session_factory(websocket.app.state.engine)
    family: TransformFamily | None = None
    candidate: TransformCandidate | None = None
    configured_glyph_target_id: UUID | None = None
    target: np.ndarray | None = None
    metric: Literal["procrustes", "frechet", "chamfer"] = "procrustes"
    try:
        while True:
            try:
                payload = await _receive_payload(websocket)
            except ValueError as exc:
                await websocket.send_bytes(_pack_message({"type": "error", "message": str(exc)}))
                continue
            message_type = payload.get("type")
            if message_type == "configure":
                try:
                    async with session_factory() as session:
                        family, candidate, target, metric, configured_glyph_target_id = await _configure(
                            payload,
                            session,
                        )
                except ValueError as exc:
                    await websocket.send_bytes(_pack_message({"type": "error", "message": str(exc)}))
                    continue
                await websocket.send_bytes(
                    _pack_message(
                        {
                            "type": "configured",
                            "candidate_id": str(candidate.id),
                            "glyph_target_id": str(configured_glyph_target_id),
                        }
                    )
                )
            elif message_type == "audio":
                if family is None or candidate is None or target is None:
                    await websocket.send_bytes(
                        _pack_message({"type": "error", "message": "send configure before audio"})
                    )
                    continue
                try:
                    frames = _audio_frames(
                        payload,
                        expected_sample_rate_hz=settings.audio_sample_rate_hz,
                        frame_length_samples=settings.audio_frame_length_samples,
                        hop_length_samples=settings.audio_hop_length_samples,
                    )
                except ValueError as exc:
                    await websocket.send_bytes(_pack_message({"type": "error", "message": str(exc)}))
                    continue
                try:
                    generated = family.forward(frames, candidate.theta)
                    distance = contour_compare(generated, target, metric)
                    score_payload = _score_payload(generated, target, distance)
                except ValueError as exc:
                    await websocket.send_bytes(_pack_message({"type": "error", "message": str(exc)}))
                    continue
                await websocket.send_bytes(_pack_message(score_payload))
            else:
                await websocket.send_bytes(_pack_message({"type": "error", "message": "unknown message type"}))
    except WebSocketDisconnect:
        return


async def _receive_payload(websocket: WebSocket) -> dict[str, object]:
    message: object = await websocket.receive()
    if not isinstance(message, dict):
        raise ValueError("live message must be a WebSocket event")
    if message.get("type") == "websocket.disconnect":
        raise WebSocketDisconnect
    data = message.get("bytes")
    if not isinstance(data, bytes):
        raise ValueError("live message must be binary MessagePack")
    return _unpack_message(data)


async def _configure(
    payload: dict[str, object],
    session: AsyncSession,
) -> tuple[TransformFamily, TransformCandidate, np.ndarray, Literal["procrustes", "frechet", "chamfer"], UUID]:
    candidate_id = _uuid_field(payload, "candidate_id")
    glyph_target_id = _uuid_field(payload, "glyph_target_id")
    metric = _metric_field(payload)
    candidate_row = await session.get(TransformCandidateRow, candidate_id)
    glyph_row = await session.get(GlyphTargetRow, glyph_target_id)
    if candidate_row is None:
        raise ValueError("candidate_id not found")
    if glyph_row is None:
        raise ValueError("glyph_target_id not found")
    candidate = TransformCandidate.model_validate(candidate_row)
    target = np.vstack(load_contours(Path(glyph_row.contour_path))).astype(np.float64)
    return build_family(candidate.family), candidate, target, metric, glyph_target_id


def _unpack_message(data: bytes) -> dict[str, object]:
    try:
        value = msgpack.unpackb(data, raw=False, strict_map_key=False)
    except (
        msgpack.exceptions.ExtraData,
        msgpack.exceptions.FormatError,
        msgpack.exceptions.StackError,
        ValueError,
    ) as exc:
        raise ValueError("live message must be valid MessagePack") from exc
    if not isinstance(value, dict):
        raise ValueError("live message must be a MessagePack map")
    if not all(isinstance(key, str) for key in value):
        raise ValueError("live message keys must be strings")
    return value


def _pack_message(payload: dict[str, object]) -> bytes:
    return msgpack.packb(payload, use_bin_type=True)


def _score_payload(generated: np.ndarray, target: np.ndarray, distance: float) -> dict[str, object]:
    """Validate finite score geometry before MessagePack serialization.

    Args:
        generated: ndarray shape (num_points, 2) dtype=float64, units=unit-square coordinates [-0.5, 0.5].
        target: ndarray shape (num_points, 2) dtype=float64, units=unit-square coordinates [-0.5, 0.5].
        distance: shape-distance scalar in metric-specific normalized units.

    Returns:
        MessagePack-ready score payload with finite contour coordinates and distance.
    """
    return {"type": "score", **validated_score_payload(generated, target, distance)}


def _uuid_field(payload: dict[str, object], key: str) -> UUID:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be a UUID string") from exc


def _metric_field(payload: dict[str, object]) -> Literal["procrustes", "frechet", "chamfer"]:
    value = payload.get("scoring_metric", "procrustes")
    if value not in _METRICS:
        raise ValueError("scoring_metric must be procrustes, frechet, or chamfer")
    return value


def _audio_frames(
    payload: dict[str, object],
    *,
    expected_sample_rate_hz: int,
    frame_length_samples: int,
    hop_length_samples: int,
) -> np.ndarray:
    """Convert PCM16 bytes to overlapping live frames.

    Args:
        payload: MessagePack map containing pcm16 bytes and sample_rate_hz.
        expected_sample_rate_hz: server live-loop sample rate.
        frame_length_samples: output frame length in samples.
        hop_length_samples: frame hop in samples.

    Returns:
        ndarray shape (num_frames, frame_length_samples) dtype=float64, normalized amplitude [-1, 1].
    """
    sample_rate = payload.get("sample_rate_hz")
    if sample_rate != expected_sample_rate_hz:
        raise ValueError("live audio sample_rate_hz must match backend audio_sample_rate_hz")
    pcm16 = payload.get("pcm16")
    if not isinstance(pcm16, bytes):
        raise ValueError("audio message requires pcm16 bytes")
    samples = np.frombuffer(pcm16, dtype="<i2").astype(np.float64) / 32768.0
    if samples.size < frame_length_samples:
        samples = np.pad(samples, (0, frame_length_samples - samples.size))
    usable = frame_length_samples + ((samples.size - frame_length_samples) // hop_length_samples) * hop_length_samples
    windows = np.lib.stride_tricks.sliding_window_view(samples[:usable], frame_length_samples)[::hop_length_samples]
    return np.ascontiguousarray(np.clip(windows, -1.0, 1.0), dtype=np.float64)
