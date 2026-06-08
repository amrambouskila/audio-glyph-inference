import { describe, expect, it } from "vitest";
import { floatToPcm16, rms } from "./pcm";

describe("pcm", () => {
  it("clips and converts float samples to little-endian pcm16 bytes", () => {
    const pcm = new Int16Array(floatToPcm16(new Float32Array([-2, -0.5, 0, 0.5, 2])).buffer);
    expect(Array.from(pcm)).toEqual([-32768, -16384, 0, 16384, 32767]);
  });

  it("computes rms with an empty guard", () => {
    expect(rms(new Float32Array())).toBe(0);
    expect(rms(new Float32Array([3, 4]))).toBeCloseTo(Math.sqrt(12.5));
  });
});
