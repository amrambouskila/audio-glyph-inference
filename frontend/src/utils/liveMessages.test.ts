import { encode } from "@msgpack/msgpack";
import { describe, expect, it } from "vitest";
import { decodeLiveResponse, encodeAudio, encodeConfigure, toPoints } from "./liveMessages";

describe("liveMessages", () => {
  it("round-trips configure and audio messages through MessagePack", () => {
    expect(
      encodeConfigure({ type: "configure", candidate_id: "c", glyph_target_id: "g", scoring_metric: "procrustes" })
    ).toBeInstanceOf(Uint8Array);
    expect(encodeAudio({ type: "audio", sample_rate_hz: 16000, pcm16: new Uint8Array([1, 2]) })).toBeInstanceOf(
      Uint8Array
    );
  });

  it("validates outbound configure and audio messages before encoding", () => {
    expect(() =>
      encodeConfigure({ type: "configure", candidate_id: " ", glyph_target_id: "g", scoring_metric: "procrustes" })
    ).toThrow("configure message");
    expect(() =>
      encodeConfigure({
        type: "configure",
        candidate_id: "c",
        glyph_target_id: "g",
        scoring_metric: "bad"
      } as never)
    ).toThrow("configure message");
    expect(() => encodeAudio({ type: "audio", sample_rate_hz: Number.NaN, pcm16: new Uint8Array() })).toThrow(
      "audio message"
    );
    expect(() => encodeAudio({ type: "audio", sample_rate_hz: 16000, pcm16: [] as never })).toThrow("audio message");
  });

  it("decodes configured, error, and score responses", () => {
    const configured = decodeLiveResponse(encode({ type: "configured", candidate_id: "c", glyph_target_id: "g" }));
    expect(configured).toEqual({ type: "configured", candidate_id: "c", glyph_target_id: "g" });
    expect(decodeLiveResponse(encode({ type: "error", message: "x" }))).toEqual({ type: "error", message: "x" });
    const score = decodeLiveResponse(
      encode({
        type: "score",
        shape_distance: 0.5,
        contours: [[0, 0]],
        target_contours: [[0.5, 0]]
      })
    );
    expect(score.type).toBe("score");
  });

  it("validates malformed responses and contour points", () => {
    expect(() => decodeLiveResponse(encode(1))).toThrow("typed object");
    expect(() => decodeLiveResponse(encode({ type: "configured", candidate_id: "c" }))).toThrow("unsupported");
    expect(() => decodeLiveResponse(encode({ type: "unknown" }))).toThrow("unsupported");
    expect(toPoints([[0.1, 0.2]])).toEqual([{ x: 0.1, y: 0.2 }]);
    expect(() => toPoints([[0.1]])).toThrow("contour point");
  });

  it("rejects non-finite score distances and contour coordinates", () => {
    expect(() =>
      decodeLiveResponse(encode({ type: "score", shape_distance: Number.NaN, contours: [[0, 0]], target_contours: [[0, 0]] }))
    ).toThrow("finite distance");
    expect(() =>
      decodeLiveResponse(
        encode({ type: "score", shape_distance: 0.5, contours: [[Number.POSITIVE_INFINITY, 0]], target_contours: [[0, 0]] })
      )
    ).toThrow("finite distance");
    expect(() => toPoints([[Number.NEGATIVE_INFINITY, 0]])).toThrow("contour point");
  });
});
