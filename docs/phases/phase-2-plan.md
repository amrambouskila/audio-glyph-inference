# Phase 2 Plan — Baseline Transform Search

**Goal.** A working `SearchEngine` that fits three baseline `TransformFamily` instances to the dataset and ranks candidates by shape distance.

**Entry gate.** Phase 1 complete.

## In scope

- `TransformFamily` protocol finalized (`name`, `parameter_space`, `forward`)
- Fourier series family: `x(t) = Σ a_k cos(k t + φ_k)`, `y(t) = Σ b_k sin(k t + ψ_k)`
- Lissajous family: two coupled oscillators driven by audio spectral moments
- Phase-space embedding family: Takens delay embedding
- `SearchEngine` with grid search + CMA-ES strategy
- Shape-distance metrics: Procrustes, Fréchet, Chamfer — each with a reference-value test
- `ExperimentTracker` backed by JSONL + Pydantic
- Endpoints: `POST /api/experiments`, `GET /api/experiments`, `GET /api/experiments/{id}`, `POST /api/inference`
- 100% coverage maintained

## Explicitly deferred

- Dynamical-system family (Phase 3)
- Symbolic regression (Phase 3)
- Live UI, WebSocket, frontend (Phase 4)
- User accounts, persistence of inference results beyond the tracker (Phase 4+)

## Exit gate

- At least one candidate transform achieves mean Procrustes shape distance below the documented Phase 2 threshold (TBD during P2 kickoff) on ≥50% of letters across ≥2 speakers in the held-out split.
- All tests green, 100% coverage, CI pipeline green.
- `docs/status.md` and `docs/versions.md` updated.