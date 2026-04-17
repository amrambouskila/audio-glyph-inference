# Versions

Semver-ordered, newest at top. Version numbers come from `backend/pyproject.toml` — never invented or guessed. The release pipeline bumps the source-of-truth field; this document only records what's in each version.

Pre-alpha convention: this project stays on `0.0.x` until the Phase 1 data pipeline actually runs end-to-end. Use **patch** bumps for incremental work during that period. `0.1.0` is reserved for the first version where `POST /api/datasets/audio` + glyph extraction work together on real data.

---

## v0.0.2 — CI wheel build fix

### Fixed

- `uv build` in GitHub Actions failed on the wheel-from-sdist step because `backend/pyproject.toml`'s `readme = "../README.md"` reached outside the package root; parent-relative paths cannot travel inside an sdist, so hatchling's metadata validation aborted the wheel build. Replaced with a dedicated `backend/README.md` and set `readme = "README.md"`. Root `README.md` remains the project-wide doc; the new file is backend-package-scoped.
- `docker-build` job failed on `backend/Dockerfile` line 41 with `Syntax error: "(" unexpected`. The dependency-install `RUN` layer used bash process substitution (`<(uv pip compile pyproject.toml)`), which `/bin/sh` (dash, the default `RUN` shell on `python:3.11-slim`) does not support. Replaced with a two-step `uv pip compile -o /tmp/requirements.txt` + `uv pip install -r /tmp/requirements.txt` (POSIX-sh compatible, same intent, cacheable).

---

## v0.0.1 — Initial scaffold + data decisions

### Decisions

- **Audio source = user-uploaded `.m4a` files only**, across five accents: `ashkenazi`, `sephardi`, `moroccan`, `yemenite`, `chabad`. No public-dataset ingester, no CLI recorder, no browser recorder. Master plan §11.1.
- **Generalization split = accent-disjoint**, leave-one-accent-out (5 rows). Master plan §11.3.
- **Glyph font = `StamAshkenazCLM.ttf`** (Culmus Project / Yoram Gnat / GPL v2). Committed at `backend/data/fonts/StamAshkenazCLM.ttf` alongside `StamAshkenazCLM.LICENSE.txt` and `StamAshkenazCLM.README.txt`. Master plan §11.2.
- **Scoring metric default = `procrustes_distance`**. Fréchet and Chamfer are tiebreakers. Master plan §11.4.

### Added

- Full project scaffold per global `CLAUDE.md` §3
- Backend skeleton: FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + PyTorch + librosa + audioread + opencv + shapely + freetype-py, managed by `uv`
- `backend/src/simulation/transforms/` with the `TransformFamily` protocol and five placeholder families (Fourier series, Lissajous, phase-space embedding, dynamical system, symbolic regression)
- `backend/src/models/` with Pydantic models for AudioSample (including `accent`), GlyphTarget, PairedExample, TransformCandidate, ExperimentRun
- `constants.ACCENTS` vocabulary (`ashkenazi`, `sephardi`, `moroccan`, `yemenite`, `chabad`) with named string constants
- Vendored font: `backend/data/fonts/StamAshkenazCLM.ttf` (~15 KB, GPL v2) + license + README
- Mirrored ORM rows under `backend/src/data/orm/`
- Docker stack: postgres 16 + redis 7 + backend, with healthchecks and `depends_on: service_healthy` gating; ffmpeg in the backend image for `.m4a` decoding
- Launcher scripts: `run_audio_glyph_inference.{sh,bat}` with `[k]/[q]/[v]/[r]` loop
- `.claude/` wiring: `settings.json` with SessionStart / PreToolUse sensitive-file block / PostToolUse contextual reminders / PreCompact / Stop hooks; permissions allow/deny; commands (scaffold, review, pre-commit, validate, phase-status, new-transform-family); skills (phase-awareness, transform-protocol, data-driven-check, validation-protocol, frontend-protocol)
- `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md` with full problem statement, data contracts, transform zoo, phase roadmap, Mermaid architecture + gantt + module-dependency diagrams, and Phase 1–5 gate checklists
- `.gitlab-ci.yml` with lint → test → coverage-gate (100%) → build → docker-build stages and manual release job

### Notes

- No logic implemented yet. All simulation methods raise `NotImplementedError`.
- The frontend (`frontend/` directory) is deliberately not scaffolded — it lands in Phase 4 per "non-applicable parts are removed, never stubbed."