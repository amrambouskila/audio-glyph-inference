import { describe, expect, it } from "vitest";
import { parseAudioSampleRateHz } from "./audioSampleRate";

describe("audioSampleRate", () => {
  it("uses the live-loop default when the env var is absent", () => {
    expect(parseAudioSampleRateHz(undefined)).toBe(16000);
  });

  it("parses positive integer env values", () => {
    expect(parseAudioSampleRateHz("48000")).toBe(48000);
  });

  it("rejects malformed sample-rate env values", () => {
    expect(() => parseAudioSampleRateHz("not-a-number")).toThrow("VITE_AUDIO_SAMPLE_RATE_HZ");
    expect(() => parseAudioSampleRateHz("0")).toThrow("VITE_AUDIO_SAMPLE_RATE_HZ");
    expect(() => parseAudioSampleRateHz("16000.5")).toThrow("VITE_AUDIO_SAMPLE_RATE_HZ");
  });
});
