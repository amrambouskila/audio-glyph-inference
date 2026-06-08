export type ThetaValue = number | string | readonly number[];

export interface AudioSampleApiModel {
  readonly id: string;
  readonly letter: string;
  readonly speaker_id: string;
  readonly accent: string;
  readonly repetition: number;
  readonly pronunciation_variant: "plain" | "hard" | "soft";
  readonly source: string;
  readonly file_path: string;
  readonly sample_rate_hz: number;
  readonly duration_s: number;
  readonly recorded_at: string;
}

export interface GlyphTargetApiModel {
  readonly id: string;
  readonly letter: string;
  readonly glyph_form: string;
  readonly font_name: string;
  readonly raster_size_px: number;
  readonly contour_path: string;
  readonly num_points: number;
  readonly num_contours: number;
}

export interface PairedExampleApiModel {
  readonly id: string;
  readonly audio_sample_id: string;
  readonly glyph_target_id: string;
  readonly letter: string;
  readonly pronunciation_variant: "plain" | "hard" | "soft";
  readonly glyph_form: string;
  readonly split: "train" | "val" | "test";
}

export interface TransformCandidateApiModel {
  readonly id: string;
  readonly family: string;
  readonly theta: Record<string, ThetaValue>;
  readonly expression: string | null;
  readonly shared_across_letters: boolean;
  readonly interpretability_score: number;
  readonly simplicity_score: number;
  readonly mean_shape_distance: number;
  readonly lookup_ratio: number;
  readonly created_at: string;
}

export interface ExperimentRunApiModel {
  readonly id: string;
  readonly name: string;
  readonly family: string;
  readonly search_strategy: "grid" | "cma-es" | "bayesian" | "symbolic-regression";
  readonly dataset_split: string;
  readonly scoring_metric: "procrustes" | "frechet" | "chamfer";
  readonly regularization_weight: number;
  readonly held_out_accent: string | null;
  readonly rng_seed: number;
  readonly font_name: string;
  readonly config_snapshot: Record<string, string | number | boolean>;
  readonly max_evaluations: number;
  readonly started_at: string;
  readonly completed_at: string | null;
  readonly best_candidate_id: string | null;
}

export interface ExperimentDetailApiModel {
  readonly run: ExperimentRunApiModel;
  readonly best_candidate: TransformCandidateApiModel | null;
  readonly candidate_count: number;
}
