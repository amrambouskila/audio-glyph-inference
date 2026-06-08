import type { ConfigureMessage } from "./live";
import type { ExperimentDetailApiModel, ExperimentRunApiModel, GlyphTargetApiModel, TransformCandidateApiModel } from "./apiModels";

export type GlyphTargetSummary = Pick<GlyphTargetApiModel, "id" | "letter" | "glyph_form" | "font_name" | "num_contours">;

export type ExperimentRunSummary = Pick<
  ExperimentRunApiModel,
  "id" | "name" | "family" | "search_strategy" | "completed_at" | "best_candidate_id"
>;

export type TransformCandidateSummary = Pick<TransformCandidateApiModel, "id" | "family" | "mean_shape_distance" | "lookup_ratio">;

export interface ExperimentDetailSummary extends Pick<ExperimentDetailApiModel, "candidate_count"> {
  readonly run: ExperimentRunSummary;
  readonly best_candidate: TransformCandidateSummary | null;
}

export interface CandidateOption {
  readonly id: string;
  readonly label: string;
}

export type ScoringMetric = ConfigureMessage["scoring_metric"];
