import { describe, expect, it } from "vitest";
import { appendScore, latestDistanceByLetter, meanDistance, updateRateHz } from "./scoreHistory";

describe("scoreHistory", () => {
  it("appends with a positive limit", () => {
    const next = appendScore(
      [
        { atMs: 1, distance: 0.4, letter: "aleph" },
        { atMs: 2, distance: 0.3, letter: "bet" }
      ],
      { atMs: 3, distance: 0.2, letter: "gimel" },
      2
    );
    expect(next).toEqual([
      { atMs: 2, distance: 0.3, letter: "bet" },
      { atMs: 3, distance: 0.2, letter: "gimel" }
    ]);
  });

  it("rejects non-positive limits and averages distances", () => {
    expect(() => appendScore([], { atMs: 1, distance: 0.1, letter: "aleph" }, 0)).toThrow("positive");
    expect(meanDistance([])).toBe(0);
    expect(
      meanDistance([
        { atMs: 1, distance: 0.2, letter: "aleph" },
        { atMs: 2, distance: 0.4, letter: "bet" }
      ])
    ).toBeCloseTo(0.3);
  });

  it("keeps the latest distance for each letter", () => {
    const latest = latestDistanceByLetter([
      { atMs: 1, distance: 0.5, letter: "aleph" },
      { atMs: 2, distance: 0.3, letter: "bet" },
      { atMs: 3, distance: 0.2, letter: "aleph" }
    ]);

    expect([...latest.entries()]).toEqual([
      ["aleph", 0.2],
      ["bet", 0.3]
    ]);
  });

  it("computes the recent score update rate", () => {
    const history = [
      { atMs: 0, distance: 0.8, letter: "aleph" },
      { atMs: 1000, distance: 0.5, letter: "aleph" },
      { atMs: 1100, distance: 0.4, letter: "aleph" },
      { atMs: 1200, distance: 0.3, letter: "aleph" }
    ];

    expect(updateRateHz(history, 1200)).toBeCloseTo(10);
    expect(updateRateHz(history, 2500)).toBe(0);
  });

  it("rejects invalid rate windows and zero elapsed samples", () => {
    expect(() => updateRateHz([], 0, 0)).toThrow("windowMs");
    expect(
      updateRateHz(
        [
          { atMs: 10, distance: 0.1, letter: "aleph" },
          { atMs: 10, distance: 0.2, letter: "bet" }
        ],
        10
      )
    ).toBe(0);
  });
});
