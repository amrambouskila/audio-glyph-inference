const DEFAULT_AUDIO_SAMPLE_RATE_HZ = 16000;

export function parseAudioSampleRateHz(value: string | undefined): number {
  if (value === undefined) {
    return DEFAULT_AUDIO_SAMPLE_RATE_HZ;
  }
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error("VITE_AUDIO_SAMPLE_RATE_HZ must be a positive integer");
  }
  return parsed;
}
