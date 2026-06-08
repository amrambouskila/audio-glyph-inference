# Phase 5 Plan - Writeup & Negative Results

**Goal.** A paper-grade analysis of what was and was not found.

**Entry gate.** Phase 4 complete.

## In scope

- `docs/writeup.md` - full writeup following a research-note structure (problem, methods, results, discussion, limitations) - scaffold implemented; empirical conclusion pending real data
- Per-family leaderboards (final tables from all experiment runs) - replay code implemented; final tables pending experiment ledgers
- Cross-accent (leave-one-accent-out) generalization tables - evaluation harness implemented; final tables pending recordings
- Analysis notebooks reproducing every table and figure (matplotlib + seaborn, not plotly) - manifest-backed notebook entrypoint implemented with transcript rendering and excluded-run-filtered leaderboard DataFrame prep; final figures pending data
- Reproducible experiment manifest committed under `backend/experiments/manifests/` - pending-real-data manifest, Stage-7 dataset audit, manifest validation, result-artifact/live-loop-evidence validation, all-glyph-form live-loop evidence template generation, and report-render command implemented
- Negative-results discussion (required, even if a successful candidate exists) - scaffold implemented; final verdict pending real-data evaluation
- Completion audit separating implemented work from external/data-dependent gates - implemented at `docs/completion-audit.md`

## Explicitly deferred

- Any new production code

## Exit gate

- A reader who has never seen the repo can reproduce every figure by reading `docs/writeup.md` and running one manifest.
- `docs/status.md` marks the project as "Phase 5 complete - maintenance mode".
