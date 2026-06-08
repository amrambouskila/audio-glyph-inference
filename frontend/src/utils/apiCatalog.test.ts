import { describe, expect, it, vi } from "vitest";
import { fetchCandidateOptions, fetchGlyphTargets } from "./apiCatalog";

function jsonResponse(value: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: () => Promise.resolve(value)
  } as Response;
}

describe("apiCatalog", () => {
  it("fetches glyph targets", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse([{ id: "glyph-1", letter: "×", glyph_form: "×", font_name: "StamAshkenazCLM.ttf", num_contours: 1 }])
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchGlyphTargets("http://api")).resolves.toEqual([
      { id: "glyph-1", letter: "×", glyph_form: "×", font_name: "StamAshkenazCLM.ttf", num_contours: 1 }
    ]);
    expect(fetchMock).toHaveBeenCalledWith("http://api/api/datasets/glyphs?limit=500");
  });

  it("rejects malformed glyph responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([{ id: "glyph-1" }])));

    await expect(fetchGlyphTargets("http://api")).rejects.toThrow("glyph.letter");

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([null])));
    await expect(fetchGlyphTargets("http://api")).rejects.toThrow("glyph target must be an object");

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([[]])));
    await expect(fetchGlyphTargets("http://api")).rejects.toThrow("glyph target must be an object");
  });

  it("rejects non-array glyph responses and invalid glyph numbers", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse({})));
    await expect(fetchGlyphTargets("http://api")).rejects.toThrow("glyph target response");

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(
        jsonResponse([{ id: "glyph-1", letter: "×", glyph_form: "×", font_name: "StamAshkenazCLM.ttf", num_contours: Number.NaN }])
      )
    );
    await expect(fetchGlyphTargets("http://api")).rejects.toThrow("glyph.num_contours");
  });

  it("fetches candidate options from completed experiment details", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse([
          {
            id: "run-1",
            name: "baseline",
            family: "lissajous",
            search_strategy: "grid",
            completed_at: "2026-06-04T00:00:00Z",
            best_candidate_id: "candidate-1"
          },
          {
            id: "run-2",
            name: "running",
            family: "fourier_series",
            search_strategy: "grid",
            completed_at: null,
            best_candidate_id: null
          }
        ])
      )
      .mockResolvedValueOnce(
        jsonResponse({
          run: {
            id: "run-1",
            name: "baseline",
            family: "lissajous",
            search_strategy: "grid",
            completed_at: "2026-06-04T00:00:00Z",
            best_candidate_id: "candidate-1"
          },
          best_candidate: {
            id: "candidate-1",
            family: "lissajous",
            mean_shape_distance: 0.12345,
            lookup_ratio: 0.42
          },
          candidate_count: 5
        })
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchCandidateOptions("http://api")).resolves.toEqual([
      { id: "candidate-1", label: "baseline / lissajous / d=0.1235" }
    ]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("rejects failed fetches", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, false, 500)));

    await expect(fetchCandidateOptions("http://api")).rejects.toThrow("returned 500");
  });

  it("rejects malformed experiment responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse({})));
    await expect(fetchCandidateOptions("http://api")).rejects.toThrow("experiment response");

    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse([null])));
    await expect(fetchCandidateOptions("http://api")).rejects.toThrow("experiment run");

    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse([[]])));
    await expect(fetchCandidateOptions("http://api")).rejects.toThrow("experiment run");

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(
        jsonResponse([
          {
            id: "run-1",
            name: "baseline",
            family: "lissajous",
            search_strategy: "nearest-neighbor",
            completed_at: "2026-06-04T00:00:00Z",
            best_candidate_id: "candidate-1"
          }
        ])
      )
    );
    await expect(fetchCandidateOptions("http://api")).rejects.toThrow("run.search_strategy");
  });

  it("rejects malformed experiment detail responses", async () => {
    const run = {
      id: "run-1",
      name: "baseline",
      family: "lissajous",
      search_strategy: "grid",
      completed_at: "2026-06-04T00:00:00Z",
      best_candidate_id: "candidate-1"
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse([run])).mockResolvedValueOnce(jsonResponse(null)));
    await expect(fetchCandidateOptions("http://api")).rejects.toThrow("experiment detail");

    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse([run])).mockResolvedValueOnce(jsonResponse([])));
    await expect(fetchCandidateOptions("http://api")).rejects.toThrow("experiment detail");

    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce(jsonResponse([run]))
        .mockResolvedValueOnce(jsonResponse({ run, best_candidate: "bad", candidate_count: 1 }))
    );
    await expect(fetchCandidateOptions("http://api")).rejects.toThrow("best_candidate");
  });

  it("skips experiment details whose best candidate is unavailable", async () => {
    const run = {
      id: "run-1",
      name: "baseline",
      family: "lissajous",
      search_strategy: "grid",
      completed_at: "2026-06-04T00:00:00Z",
      best_candidate_id: "candidate-1"
    };
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce(jsonResponse([run]))
        .mockResolvedValueOnce(jsonResponse({ run, best_candidate: null, candidate_count: 0 }))
    );

    await expect(fetchCandidateOptions("http://api")).resolves.toEqual([]);
  });
});

