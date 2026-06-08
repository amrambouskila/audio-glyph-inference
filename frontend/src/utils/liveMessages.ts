import { decode, encode } from "@msgpack/msgpack";
import type { AudioMessage, ConfigureMessage, LiveResponse, Point2D, ScoreResponse } from "../types/live";

interface ScoreRecord extends Record<string, unknown> {
  readonly shape_distance: number;
  readonly contours: readonly (readonly number[])[];
  readonly target_contours: readonly (readonly number[])[];
}

export function encodeConfigure(message: ConfigureMessage): Uint8Array {
  if (
    message.candidate_id.trim().length === 0 ||
    message.glyph_target_id.trim().length === 0 ||
    !isScoringMetric(message.scoring_metric)
  ) {
    throw new Error("configure message requires candidate id, glyph target id, and scoring metric");
  }
  return encode(message);
}

export function encodeAudio(message: AudioMessage): Uint8Array {
  if (!Number.isInteger(message.sample_rate_hz) || message.sample_rate_hz <= 0 || !(message.pcm16 instanceof Uint8Array)) {
    throw new Error("audio message requires a positive integer sample_rate_hz and pcm16 bytes");
  }
  return encode(message);
}

export function decodeLiveResponse(payload: ArrayBuffer | Uint8Array): LiveResponse {
  const value = decode(payload);
  if (!isRecord(value) || typeof value.type !== "string") {
    throw new Error("live response must be a typed object");
  }
  if (
    value.type === "configured" &&
    typeof value.candidate_id === "string" &&
    typeof value.glyph_target_id === "string"
  ) {
    return { type: "configured", candidate_id: value.candidate_id, glyph_target_id: value.glyph_target_id };
  }
  if (value.type === "error" && typeof value.message === "string") {
    return { type: "error", message: value.message };
  }
  if (value.type === "score") {
    if (!isScoreResponse(value)) {
      throw new Error("score response must contain finite distance and point arrays");
    }
    return {
      type: "score",
      shape_distance: value.shape_distance,
      contours: value.contours,
      target_contours: value.target_contours
    };
  }
  throw new Error(`unsupported live response type ${value.type}`);
}

export function toPoints(contour: ScoreResponse["contours"]): Point2D[] {
  return contour.map((point) => {
    if (point.length !== 2 || !isFiniteNumber(point[0]) || !isFiniteNumber(point[1])) {
      throw new Error("contour point must be [x, y]");
    }
    return { x: point[0], y: point[1] };
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isScoreResponse(value: Record<string, unknown>): value is ScoreRecord {
  return (
    isFiniteNumber(value.shape_distance) &&
    isPointArray(value.contours) &&
    isPointArray(value.target_contours)
  );
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isScoringMetric(value: unknown): value is ConfigureMessage["scoring_metric"] {
  return value === "procrustes" || value === "frechet" || value === "chamfer";
}

function isPointArray(value: unknown): value is readonly (readonly number[])[] {
  return (
    Array.isArray(value) &&
    value.every(
      (point) =>
        Array.isArray(point) &&
        point.length === 2 &&
        isFiniteNumber(point[0]) &&
        isFiniteNumber(point[1])
    )
  );
}
