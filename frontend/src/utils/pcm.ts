export function floatToPcm16(samples: Float32Array): Uint8Array {
  const output = new Int16Array(samples.length);
  for (let index = 0; index < samples.length; index += 1) {
    const clipped = Math.max(-1, Math.min(1, samples[index]));
    output[index] = Math.round(clipped < 0 ? clipped * 32768 : clipped * 32767);
  }
  return new Uint8Array(output.buffer);
}

export function rms(samples: Float32Array): number {
  if (samples.length === 0) {
    return 0;
  }
  let sum = 0;
  for (const sample of samples) {
    sum += sample * sample;
  }
  return Math.sqrt(sum / samples.length);
}
