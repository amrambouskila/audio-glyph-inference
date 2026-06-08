export interface ScoreSample {
  readonly atMs: number;
  readonly distance: number;
  readonly letter: string;
}

export function appendScore(history: readonly ScoreSample[], sample: ScoreSample, limit: number): ScoreSample[] {
  if (limit <= 0) {
    throw new Error("limit must be positive");
  }
  return [...history, sample].slice(-limit);
}

export function meanDistance(history: readonly ScoreSample[]): number {
  if (history.length === 0) {
    return 0;
  }
  return history.reduce((sum, item) => sum + item.distance, 0) / history.length;
}

export function latestDistanceByLetter(history: readonly ScoreSample[]): Map<string, number> {
  const latest = new Map<string, number>();
  for (const sample of history) {
    latest.set(sample.letter, sample.distance);
  }
  return latest;
}

export function updateRateHz(history: readonly ScoreSample[], nowMs: number, windowMs = 1000): number {
  if (windowMs <= 0) {
    throw new Error("windowMs must be positive");
  }
  const windowStart = nowMs - windowMs;
  const visible = history.filter((sample) => sample.atMs >= windowStart && sample.atMs <= nowMs);
  if (visible.length < 2) {
    return 0;
  }
  const last = visible[visible.length - 1];
  const first = visible[0];
  const elapsedMs = last.atMs - first.atMs;
  if (elapsedMs <= 0) {
    return 0;
  }
  return ((visible.length - 1) * 1000) / elapsedMs;
}
