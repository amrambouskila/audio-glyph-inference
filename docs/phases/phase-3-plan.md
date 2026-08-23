# Phase 3 Plan - Expanded Search Space

**Goal.** Expand the transform zoo and measure generalization rigorously across accents (leave-one-accent-out; single speaker - see master plan §11.3).

**Entry gate.** Phase 2 complete with a working baseline.

**Implementation status:** Phase-3 buildable work has started while Phase-2 empirical gates wait on recordings. `DynamicalSystemFamily` is implemented and registered with Van der Pol / Duffing / resonator modes and closed-form reference tests. `SearchEngine(strategy="bayesian")` is implemented as a deterministic Gaussian-process / expected-improvement optimizer over the existing normalized `ParameterSpec` decoder, with config-driven initial sample count, candidate pool size, RBF length scale, and noise jitter. The symbolic-regression expression conversion/evaluation layer is implemented and registered for saved-candidate inference; the optional PySR proposal/search path is implemented behind `[symbolic]`. The leave-one-accent-out evaluation harness is implemented as a pure simulation/report module; the real-data report still awaits Stage-7 recordings. Per-family leaderboards are implemented from JSONL tracker replay. Negative-results scaffolding is implemented as a docs template plus pure Markdown renderer.

## In scope

- Dynamical-system family (Van der Pol, Duffing, coupled resonators) driven by audio
- Bayesian `SearchEngine` strategy over the existing low-dimensional searched `ParameterSpec` knobs - implemented
- Symbolic-regression family via PySR, behind the `[symbolic]` extra - implemented
- Expression -> `TransformFamily` conversion pipeline (PySR output -> explicit callable) - implemented
- Leave-one-accent-out evaluation harness with accent-disjoint splits - implemented; real-data report pending recordings
- Per-family leaderboards in the experiment tracker - implemented from JSONL replay
- Negative-results reporting scaffolding (`docs/negative-results.md`) - implemented

## Explicitly deferred

- Live UI, WebSocket, frontend (Phase 4)

## Exit gate

One of:

- (a) A shared-across-letters candidate beats the Phase 2 baseline with statistical significance on the held-out accent, documented in a results note, OR
- (b) A negative-results writeup explains the search transcript and the sufficiency of the search space tested.

In either case:

- SAST stage green — zero HIGH/CRITICAL findings; MEDIUM findings triaged with written justification.
- New input boundaries in this phase are injection-safe and documented in `CLAUDE.md` `<security>`.
