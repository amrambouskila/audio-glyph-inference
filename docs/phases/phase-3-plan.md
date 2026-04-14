# Phase 3 Plan — Expanded Search Space

**Goal.** Expand the transform zoo and measure generalization rigorously across speakers.

**Entry gate.** Phase 2 complete with a working baseline.

## In scope

- Dynamical-system family (Van der Pol, Duffing, coupled resonators) driven by audio
- Symbolic-regression family via PySR, behind the `[symbolic]` extra
- Expression → `TransformFamily` conversion pipeline (PySR output → explicit callable)
- Cross-speaker evaluation harness with speaker-disjoint splits
- Per-family leaderboards in the experiment tracker
- Negative-results reporting scaffolding (`docs/negative-results.md`)

## Explicitly deferred

- Live UI, WebSocket, frontend (Phase 4)

## Exit gate

One of:
- (a) A shared-across-letters candidate beats the Phase 2 baseline with statistical significance on held-out speakers, documented in a results note, OR
- (b) A negative-results writeup explains the search transcript and the sufficiency of the search space tested.