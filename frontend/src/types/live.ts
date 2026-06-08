export interface Point2D {
  readonly x: number;
  readonly y: number;
}

export interface ConfigureMessage {
  readonly type: "configure";
  readonly candidate_id: string;
  readonly glyph_target_id: string;
  readonly scoring_metric: "procrustes" | "frechet" | "chamfer";
}

export interface AudioMessage {
  readonly type: "audio";
  readonly sample_rate_hz: number;
  readonly pcm16: Uint8Array;
}

export interface ConfiguredResponse {
  readonly type: "configured";
  readonly candidate_id: string;
  readonly glyph_target_id: string;
}

export interface ScoreResponse {
  readonly type: "score";
  readonly shape_distance: number;
  readonly contours: readonly (readonly number[])[];
  readonly target_contours: readonly (readonly number[])[];
}

export interface ErrorResponse {
  readonly type: "error";
  readonly message: string;
}

export type LiveResponse = ConfiguredResponse | ScoreResponse | ErrorResponse;
