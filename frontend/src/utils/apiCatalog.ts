import type { CandidateOption, ExperimentDetailSummary, ExperimentRunSummary, GlyphTargetSummary } from "../types/catalog";
import type { ExperimentRunApiModel } from "../types/apiModels";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireString(value: unknown, field: string): string {
  if (typeof value !== "string") {
    throw new Error(`${field} must be a string`);
  }
  return value;
}

function optionalString(value: unknown, field: string): string | null {
  if (value === null) {
    return null;
  }
  return requireString(value, field);
}

function requireSearchStrategy(value: unknown): ExperimentRunApiModel["search_strategy"] {
  const strategy = requireString(value, "run.search_strategy");
  if (strategy !== "grid" && strategy !== "cma-es" && strategy !== "bayesian" && strategy !== "symbolic-regression") {
    throw new Error("run.search_strategy must be a known strategy");
  }
  return strategy;
}

function requireNumber(value: unknown, field: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`${field} must be a finite number`);
  }
  return value;
}

function parseGlyphTarget(value: unknown): GlyphTargetSummary {
  if (!isRecord(value)) {
    throw new Error("glyph target must be an object");
  }
  return {
    id: requireString(value.id, "glyph.id"),
    letter: requireString(value.letter, "glyph.letter"),
    glyph_form: requireString(value.glyph_form, "glyph.glyph_form"),
    font_name: requireString(value.font_name, "glyph.font_name"),
    num_contours: requireNumber(value.num_contours, "glyph.num_contours")
  };
}

function parseExperimentRun(value: unknown): ExperimentRunSummary {
  if (!isRecord(value)) {
    throw new Error("experiment run must be an object");
  }
  return {
    id: requireString(value.id, "run.id"),
    name: requireString(value.name, "run.name"),
    family: requireString(value.family, "run.family"),
    search_strategy: requireSearchStrategy(value.search_strategy),
    completed_at: optionalString(value.completed_at, "run.completed_at"),
    best_candidate_id: optionalString(value.best_candidate_id, "run.best_candidate_id")
  };
}

function parseExperimentDetail(value: unknown): ExperimentDetailSummary {
  if (!isRecord(value)) {
    throw new Error("experiment detail must be an object");
  }
  const bestCandidate = value.best_candidate;
  if (bestCandidate !== null && !isRecord(bestCandidate)) {
    throw new Error("best_candidate must be an object or null");
  }
  return {
    run: parseExperimentRun(value.run),
    best_candidate:
      bestCandidate === null
        ? null
        : {
            id: requireString(bestCandidate.id, "candidate.id"),
            family: requireString(bestCandidate.family, "candidate.family"),
            mean_shape_distance: requireNumber(bestCandidate.mean_shape_distance, "candidate.mean_shape_distance"),
            lookup_ratio: requireNumber(bestCandidate.lookup_ratio, "candidate.lookup_ratio")
          },
    candidate_count: requireNumber(value.candidate_count, "candidate_count")
  };
}

async function fetchJson(baseUrl: string, path: string): Promise<unknown> {
  const response = await fetch(`${baseUrl}${path}`);
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }
  return response.json();
}

export async function fetchGlyphTargets(baseUrl: string): Promise<GlyphTargetSummary[]> {
  const value = await fetchJson(baseUrl, "/api/datasets/glyphs?limit=500");
  if (!Array.isArray(value)) {
    throw new Error("glyph target response must be an array");
  }
  return value.map(parseGlyphTarget);
}

export async function fetchCandidateOptions(baseUrl: string): Promise<CandidateOption[]> {
  const runsValue = await fetchJson(baseUrl, "/api/experiments?status=completed&limit=50");
  if (!Array.isArray(runsValue)) {
    throw new Error("experiment response must be an array");
  }
  const runs = runsValue.map(parseExperimentRun).filter((run) => run.best_candidate_id !== null);
  const details = await Promise.all(
    runs.map((run) => fetchJson(baseUrl, `/api/experiments/${run.id}`).then(parseExperimentDetail))
  );
  return details.flatMap((detail) => {
    const candidate = detail.best_candidate;
    if (candidate === null) {
      return [];
    }
      return {
        id: candidate.id,
        label: `${detail.run.name} / ${candidate.family} / d=${candidate.mean_shape_distance.toFixed(4)}`
      };
  });
}
