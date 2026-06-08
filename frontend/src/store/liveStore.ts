import { create } from "zustand";
import type { Point2D } from "../types/live";
import { appendScore, type ScoreSample } from "../utils/scoreHistory";

interface LiveState {
  readonly candidateId: string;
  readonly glyphTargetId: string;
  readonly status: "idle" | "connected" | "streaming" | "error";
  readonly selectedLetter: string;
  readonly generated: Point2D[];
  readonly target: Point2D[];
  readonly scoreHistory: ScoreSample[];
  readonly error: string | null;
  readonly setCandidateId: (value: string) => void;
  readonly setGlyphTargetId: (value: string) => void;
  readonly setSelectedLetter: (value: string) => void;
  readonly setStatus: (value: LiveState["status"]) => void;
  readonly setError: (value: string | null) => void;
  readonly acceptScore: (generated: Point2D[], target: Point2D[], distance: number, atMs: number, letter: string) => void;
}

export const useLiveStore = create<LiveState>((set) => ({
  candidateId: "",
  glyphTargetId: "",
  status: "idle",
  selectedLetter: "",
  generated: [],
  target: [],
  scoreHistory: [],
  error: null,
  setCandidateId: (value) => set({ candidateId: value }),
  setGlyphTargetId: (value) => set({ glyphTargetId: value }),
  setSelectedLetter: (value) => set({ selectedLetter: value }),
  setStatus: (value) => set({ status: value }),
  setError: (value) => set(value === null ? { error: null } : { error: value, status: "error" }),
  acceptScore: (generated, target, distance, atMs, letter) =>
    set((state) => ({
      generated,
      target,
      status: "streaming",
      error: null,
      scoreHistory: appendScore(state.scoreHistory, { atMs, distance, letter }, 120)
    }))
}));
