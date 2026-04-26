---
name: phase-awareness
description: Proactively applied at session start and before any implementation work; orients Codex to the current phase and its explicit scope constraints
---

# Phase Awareness

This project is phased. Work that makes sense in Phase 3 is out of scope in Phase 1, and vice versa. Before implementing anything, identify the current phase and respect its scope.

## Protocol

1. Read `docs/status.md` — the top of the file names the current phase.
2. Read `docs/phases/phase-{N}-plan.md` for that phase. Its "In scope" and "Explicitly deferred" sections are load-bearing.
3. Before implementing, ask yourself: *does this work land inside the current phase's scope?* If not, stop and flag it.

## Hard constraints per phase

- **Phase 1 — Data pipeline.** Build: audio ingestion, preprocessing, glyph rendering, contour extraction, paired-example storage, minimal FastAPI with health + dataset endpoints. Do NOT build: transform search engines, candidate ranking, live UI, WebSocket streaming.
- **Phase 2 — Baseline transform search.** Build: the `TransformFamily` protocol, three baseline families (Fourier, Lissajous, phase-space), `SearchEngine`, shape-distance metrics, experiment tracker. Do NOT build: dynamical systems, symbolic regression, PySR, live UI.
- **Phase 3 — Expanded search space.** Build: dynamical-system families, symbolic regression via PySR (optional dep), cross-speaker generalization eval. Do NOT build: live UI.
- **Phase 4 — Live pronunciation UI.** Build: React 18 + TS strict + Vite + R3F frontend, WebSocket `/ws/live` with MessagePack frames, Chart.js scoring dashboard. Scaffolds the `frontend/` directory for the first time.
- **Phase 5 — Writeup.** Build: paper-grade analysis, negative-results reporting. No new production code.

## When the user asks for something out of phase

Flag it. Example: "That change belongs in Phase 3 (symbolic regression). We're currently in Phase 2 — the baseline search engine doesn't exist yet. Do you want to finish Phase 2 first, or explicitly re-prioritize?"