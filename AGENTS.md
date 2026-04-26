# AGENTS.md — audio-glyph-inference

> **MANDATORY WORKFLOW: READ THIS ENTIRE FILE BEFORE EVERY CHANGE.** Every time. No skimming, no assuming prior-session context carries over — it does not.
>
> **Why:** This project spans multiple sessions and months of development. Skipping the re-read produces decisions that contradict the architecture, duplicate existing patterns, break data contracts, or introduce tech debt that compounds.
>
> **The workflow, every time:**
> 1. Read this entire file in full.
> 2. Read `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md` in full.
> 3. Read `docs/status.md` — current state / what was just built.
> 4. Read `docs/versions.md` — recent version history (top few entries).
> 5. Read `docs/phases/phase-{N}-plan.md` for the current phase.
> 6. **If touching the audio ingestion pipeline** (`src/api/routers/datasets.py`, `src/simulation/audio_preprocessor.py`, `src/config.py`'s audio fields, or the `AudioSample` model) — also read `docs/recording_protocol.md`. It locks duration, loudness, articulation, storage layout, and server validation rules that the code is expected to enforce.
> 7. Read the source files you plan to modify — understand existing patterns first.
> 8. Then implement, following the rules and contracts defined here.
>
> If a request conflicts with the master plan, stop and flag it before implementing.

---

## 0. Critical context — what this project IS and IS NOT

### What it is

**A system-identification / operator-inference problem.** The input distribution is given (recordings of spoken Hebrew letters). The output distribution is given (canonical glyph contours rendered from a STAM-style Torah font). The unknown object is the **transformation itself** — a compact, interpretable, generalizable mathematical operator

```text
    F_θ : x(t) → G
```

that maps an audio waveform `x(t)` to a 2D contour `G`, parameterized by `θ`. The fitting problem is

```text
    θ* = argmin_θ  Σ d(F_θ(x_i), L_i)  +  λ · Complexity(F_θ)
```

across paired examples `(x_i, L_i)` of (audio sample, target glyph), with `d(·,·)` a shape distance metric.

### What it is NOT

- **Not a classifier.** We do not predict the letter label. Given the audio, we already know the label — the label is used to select `L_i`. The question is about the transformation, not the category.
- **Not a generative model in the modern sense.** No GAN, no diffusion, no latent-to-pixel autoencoder as the main solution. Neural nets are acceptable only as candidate *proposers* whose output is then distilled into explicit symbolic math.
- **Not a decorative visualization pipeline.** No hand-drawn shaping. No manual nudging of outputs "to look like letters." No artisanal per-letter tweaking. If the search finds nothing, we report that — we do not cheat the visuals.
- **Not a standalone phoneme → glyph lookup.** A trivial lookup table trivially satisfies the input-output mapping but explains nothing. Candidate transforms must be explicit operators; a lookup-table-disguised-as-math is a bug, not a solution.

### The core constraint you must hold in your head

> **The unknown is the algorithm.** Whenever you are tempted to "just make it work" for a specific letter, stop. That is the failure mode this project is specifically designed to avoid.

### Phase you are currently in

**Phase 1 — Data pipeline.** Scaffold-only at time of writing. Nothing in `backend/src/simulation/` or `backend/src/data/` is implemented; every method raises `NotImplementedError`. Read `docs/status.md` for the live phase state — this file may be stale.

---

## 1. Project Identity

- **What:** Research-grade experimental system inferring a mathematically interpretable mapping from spoken Hebrew-letter audio to Hebrew-letter glyph geometry.
- **Where:** `audio-glyph-inference/` — standalone repo, no parent monorepo.
- **Master plan:** `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md`. **Authoritative source for goals, data contracts, phase gates, and architectural decisions.** Read before any non-trivial task.
- **Phase file (current phase only):** `docs/phases/phase-{N}-plan.md`.
- **Status doc:** `docs/status.md`.
- **Changelog:** `docs/versions.md`.
- **Not a monorepo.** No parent `oft/`-style structure. Local stack only.

## 2. Phase Constraints

### Current phase: 1 (data pipeline)

**In scope for Phase 1:**
- Audio ingestion (upload endpoint + optional public-dataset ingester)
- Audio preprocessing: load → resample → loudness-normalize → frame
- Glyph rendering from STAM-style Torah font via freetype-py
- Contour extraction and normalization to the unit square `[-0.5, 0.5]`
- Postgres persistence for `AudioSample`, `GlyphTarget`, `PairedExample`
- Alembic migrations
- Minimal FastAPI: `/health`, `POST /api/datasets/audio`, `POST /api/datasets/glyphs`, `POST /api/datasets/pairs`, `GET /api/datasets/pairs`
- Pytest at 100% coverage across `backend/src/`
- GitLab CI pipeline green

**Explicitly deferred (do NOT build in Phase 1):**
- `SearchEngine` logic beyond signature stubs
- Transform families beyond signature stubs (the protocol is finalized; concrete `forward()` bodies are Phase 2+)
- Shape-distance metric implementations beyond signature stubs
- Any WebSocket endpoint
- **The entire `frontend/` directory.** It does not exist yet and **will not be created in Phase 1.** Phase 4 is when it lands.
- PySR / symbolic regression (Phase 3)
- Dynamical-system transform family (Phase 3)
- Any form of candidate ranking UI
- User accounts / persistence of user recordings (Phase 4+)

### When a request is out of phase

Flag it. Example:

> "That change belongs in Phase 3 (the dynamical-system family). We're currently in Phase 1 — the `SearchEngine` and baseline families don't exist yet. Do you want to finish Phase 1 first, or explicitly re-prioritize?"

Do not silently accept out-of-phase work.

## 3. Architecture & Code Rules

These extend the global `~/.codex/AGENTS.md` rules. Where they differ, the project rules win for this project.

### One concept per file (OOP rule)

Every class, Pydantic model, SQLAlchemy row, custom hook, standalone utility function, and `TransformFamily` implementation **lives in its own file**. No god files. No `utils.py` with 40 functions.

Concretely for this project:
- `backend/src/models/audio_sample.py` contains the `AudioSample` Pydantic class — nothing else.
- `backend/src/data/orm/audio_sample_row.py` contains the `AudioSampleRow` ORM class — nothing else.
- `backend/src/simulation/transforms/fourier_series.py` contains the `FourierSeriesFamily` class — nothing else.
- `backend/src/simulation/shape_distance.py` is the one exception: the three distance *functions* (Procrustes, Fréchet, Chamfer) are all closely related free functions operating on the same contract, and splitting them into three files adds friction without benefit. All three live here.

When you're about to add a new class or family, use `/scaffold` (see `.codex/commands/scaffold.md`). Do NOT hand-roll the file layout.

### Search before writing

Before creating any new class, function, or helper, **grep the existing tree first**. This is mandatory. Common violations this rule prevents:
- Re-implementing a Procrustes alignment when `shape_distance.procrustes_distance` already exists.
- Creating a second audio-frame normalizer because you forgot `AudioPreprocessor` already handles it.
- Hard-coding the Hebrew alphabet inline instead of importing `constants.HEBREW_LETTERS`.

If what you're about to write feels similar to something you've seen, **stop and check**.

### Data-driven, not hard-coded

Only `backend/src/constants.py` may contain literal numeric or string values with domain meaning. Everything else comes from:
- `backend/src/config.BackendSettings` — Pydantic Settings loaded from the environment.
- The database — paired examples, font references, experiment runs.
- Data files — glyph contours in `backend/data/contours/`, raw audio in `backend/data/audio/`, font files in `backend/data/fonts/`.
- Transform family `parameter_space()` — every θ component used by `forward()` must be declared here.

Acceptable literal numbers in logic:
- Mathematical constants (0, 1, 2, π, e)
- Array dimensions and loop bounds derived from inputs
- Algorithm coefficients intrinsic to a finite-difference or integration scheme
- Default parameter values in function signatures, documented alongside the default

Unacceptable: `sample_rate = 16000`, `font_path = "..."`, `num_contour_points = 256`, `letters = "אבגדה..."` — all of these belong in `config.py` or `constants.py`.

### No loops in numerical hot paths

Python-level iteration over frames, particles, samples, or contour points in any performance-sensitive module is a bug. Vectorize with NumPy / SciPy, or wrap with `@numba.jit(nopython=True)`. Scoring thousands of candidates against the dataset must be batched.

### Every array is typed in its docstring

Any function that accepts or returns a NumPy array documents the shape, dtype, and unit system on a single line in its docstring. Example:

```python
def forward(self, audio: np.ndarray, theta: dict[str, float]) -> np.ndarray:
    """Map preprocessed audio to a closed 2D contour.

    Args:
        audio: ndarray shape (num_frames, frame_length) dtype=float64, units=normalized amplitude [-1, 1].
        theta: fitted parameter dict with keys in parameter_space().

    Returns:
        ndarray shape (num_points, 2) dtype=float64, units=unit-square coordinates [-0.5, 0.5].
    """
```

### TransformFamily protocol is sacred

Every file under `backend/src/simulation/transforms/` implements this exact protocol. See `backend/src/simulation/transforms/transform_base.py` for the definition and the `transform-protocol` skill under `.agents/skills/` for the invariant checklist.

Summary of invariants, restated here because they matter:
1. `name()` returns a unique family string matching `TransformCandidate.family`.
2. `parameter_space()` declares every θ key used inside `forward()` — no undeclared parameters.
3. `forward()` is a pure function of `(audio, theta)`. No globals, no file I/O, no unseeded RNG.
4. `forward()` returns `ndarray (N, 2) float64` in the unit square. Anything else is a bug.
5. Configuration (sample rate, raster size, contour point count) comes from `config.BackendSettings`, not from `__init__` parameters on the family class. The family is stateless except for its type.

### Engines are standalone

Every module under `backend/src/simulation/` must be importable and usable without the FastAPI app layer or a live database. No hidden `from src.api import ...`. No hidden `from src.data.database import ...` inside a simulation module. If a simulation module needs data, the caller passes it in — it does not fetch.

### Separation of concerns between Pydantic and SQLAlchemy

- **Pydantic models** (`backend/src/models/*.py`) own API contracts and in-memory validation.
- **SQLAlchemy ORM rows** (`backend/src/data/orm/*.py`) own storage.
- **The two are wired together with explicit `model_validate(row, from_attributes=True)` conversion** at the API boundary. Never unified into one class. Never routed around via direct ORM-to-JSON serialization.
- `SQLModel` is not in use. If you want to use it as a convenience shim later, raise it first — don't silently import it.

### Data contracts are sacred

The field names and types in `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md` §3 are binding. They appear identically in:
1. Pydantic models under `backend/src/models/`
2. SQLAlchemy ORM rows under `backend/src/data/orm/`
3. Any future API request/response schemas
4. Any future TypeScript interfaces in the Phase 4 frontend

Changing any field name, type, nullability, or meaning is a **major semver bump**. Stop and ask the user before doing it. Update the master plan first, then the models, then the ORM, then the tests.

### Type safety

- Full type annotations on every Python function, method, and class attribute (`ANN` ruff rules enforced).
- No `Any` unless the user approves it and the reason is documented inline.
- No `# type: ignore` without a one-line reason comment.

### Comments: default to none

Code should be self-explanatory via naming. Write a comment only when the *why* is non-obvious: a hidden constraint, a subtle invariant, a workaround for a specific numerical pitfall. Never write comments that restate the code. Never write multi-paragraph docstrings — one short line for single-function docstrings, plus the array shape/dtype/units line if applicable.

### No dead code, no commented-out blocks, no TODOs without linked tasks

Git remembers. If it's not used, delete it. If it's worth flagging, track it. If it's not worth tracking, fix it or delete it.

---

## 4. Containerization

`audio-glyph-inference/docker-compose.yml` defines a multi-service stack.

### Phase 1 services

| Service    | Image                | Purpose                                                    |
|------------|----------------------|------------------------------------------------------------|
| `postgres` | `postgres:16-alpine` | Persistent store for paired examples + experiment runs    |
| `redis`    | `redis:7-alpine`     | Cache / pubsub, reserved for Phase 4 live streaming        |
| `backend`  | `./backend/Dockerfile` | FastAPI + all numerics (Python 3.11-slim + uv)           |

Every service has a `healthcheck`. The backend gates on `postgres: service_healthy` and `redis: service_healthy`. The backend image bakes `libsndfile1` / `libgl1` / `libglib2.0-0` / `ffmpeg` so `librosa`, `soundfile`, and `opencv-python-headless` all load correctly.

**Ports come from `.env` via `${VAR:-default}` substitution.** Never hard-code ports in compose.

### Phase 4 addition

When Phase 4 begins:
- Scaffold `frontend/` per the global AGENTS.md §5 frontend stack.
- Add a `frontend` service to `docker-compose.yml` with `depends_on: { backend: { condition: service_healthy } }`.
- Extend the launcher banner to list the frontend port.
- Do NOT touch the existing Phase 1 services.

### Why slim, not Alpine, for Python

Scientific Python (`torch`, `scipy`, `numba`, `opencv`) ships wheels built against glibc. Alpine's musl libc either breaks the wheels or forces source compilation at image build time. Use `python:3.11-slim` (Debian-based) per global AGENTS.md §9.

### Launcher contract

The root-level `run_audio_glyph_inference.sh` and `run_audio_glyph_inference.bat` implement the global AGENTS.md §4 launcher contract:
1. Print a banner listing services and ports.
2. `docker compose up --build -d`.
3. Poll `http://localhost:${BACKEND_PORT}/health` until ready.
4. Print the "services running" block with clickable URLs.
5. Enter the `[k] [q] [v] [r]` loop — repeatable restart, terminal stop variants, unrecognized input reprints the menu.
6. Port numbers come from env with `${VAR:-default}` defaults.

If the user reports the launcher looks different from `llm-knowledge-base`'s, check whether global AGENTS.md has been updated since this project was scaffolded — the canonical template lives there.

---

## 5. CI/CD

`.gitlab-ci.yml` at the project root. Stages in order:

1. **`lint`** — `ruff check .` and `ruff format --check .` inside `backend/`
2. **`test`** — `pytest --cov` with the 100% gate enforced in `backend/pyproject.toml` (`--cov-fail-under=100`)
3. **`build`** — `uv build` sdist + wheel
4. **`docker`** — `docker build` against `backend/Dockerfile` to verify the container still builds (staging/main only)
5. **`release`** — manual, triggered by "Run pipeline on `main` with `BUMP` variable", uses `uv version --bump` to bump `backend/pyproject.toml`'s version, commits + tags + pushes

**Coverage gate is 100%.** When coverage drops, the `test` job fails and `build` is automatically blocked. Fix by adding tests — never by lowering the threshold. `pragma: no cover` is allowed sparingly on genuinely untestable lines (`if __name__ == "__main__":`, platform-specific branches, `raise NotImplementedError` in Phase 1 stubs).

**You do NOT edit `backend/pyproject.toml`'s `version` field directly.** The release pipeline owns it. You only update `docs/versions.md` with the computed next version.

---

## 6. Environment Configuration

`.env` at the project root. Committed with placeholder / development defaults. Real secrets (if any are ever needed) go in `.env.local` which is gitignored.

Variable pattern: `BACKEND_*`, `POSTGRES_*`, `REDIS_*`. See `backend/src/config.BackendSettings` for the Pydantic loader that reads them.

**Forward-compat note.** The file already reserves Phase 4 vars (`VITE_PORT`, `VITE_API_BASE_URL`, `VITE_WS_URL`) commented out. Uncomment them when the frontend lands, not before.

---

## 7. Observability

Phase 1: logs only. `docker compose logs -f backend` streams uvicorn output. Use structured `logging` (via `logging.getLogger(__name__)`) inside source modules; do not scatter `print()` calls.

Phase 4+: TBD. Update `docs/run_guide.md` when an observability stack lands.

---

## 8. Domain Model & Data Contracts

The canonical data shapes are defined in `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md` §3 and summarized here. **The master plan is authoritative** — if this file and the master plan disagree, the master plan wins and this file must be fixed.

### 8.1 Hebrew letter label space

The 22 standard letters of the alef-bet, in canonical order. Exposed as `constants.HEBREW_LETTERS`. Sofit forms are visual variants handled at the glyph layer, not the audio layer — they share phonemes with their base letters. Niqqud (vowel marks) are out of scope.

### 8.2 AudioSample (Pydantic: `src/models/audio_sample.py`)

One raw recording of one letter. Fields: `id`, `letter`, `speaker_id`, `accent`, `source`, `file_path`, `sample_rate_hz`, `duration_s`, `recorded_at`. `accent` is one of `constants.ACCENTS` (`ashkenazi` / `sephardi` / `moroccan` / `yemenite` / `chabad`) and is the primary generalization axis for this project. Source paths are absolute inside the container.

### 8.3 GlyphTarget (Pydantic: `src/models/glyph_target.py`)

Canonical 2D target shape for one letter, rendered from a STAM-style Torah font. Fields: `id`, `letter`, `font_name`, `raster_size_px`, `contour_path`, `num_points`. Contour coordinates are always in the unit square `[-0.5, 0.5]` with origin at centroid — never raw pixels.

### 8.4 PairedExample (Pydantic: `src/models/paired_example.py`)

Atomic training unit. Fields: `id`, `audio_sample_id`, `glyph_target_id`, `letter`, `split`. `split` is **accent-disjoint** (`train` / `val` / `test`) — the headline generalization test is leave-one-accent-out across `ashkenazi` / `sephardi` / `moroccan` / `yemenite` / `chabad`. See master plan §11.3.

### 8.5 TransformCandidate (Pydantic: `src/models/transform_candidate.py`)

A frozen `F_θ` produced by a search run. Fields: `id`, `family`, `theta`, `shared_across_letters`, `interpretability_score`, `simplicity_score`, `mean_shape_distance`, `created_at`.

### 8.6 ExperimentRun (Pydantic: `src/models/experiment_run.py`)

One configured search. Fields: `id`, `name`, `family`, `search_strategy`, `dataset_split`, `scoring_metric`, `max_evaluations`, `started_at`, `completed_at`, `best_candidate_id`.

### 8.7 Contract invariants

- Any change to a field name, type, nullability, or semantic meaning is a major semver bump — ask the user first.
- The Pydantic model, the ORM row, and (in Phase 4) the TypeScript interface must match field-for-field.
- API request/response schemas derive from the Pydantic models — they do not diverge silently.

---

## 9. Required calculations / formulas

This project has one equation that matters. Everything else is implementation.

### 9.1 The fit

Given a family `F_θ`, a dataset slice `{(x_i, L_i)}`, a shape distance `d(·,·)`, and a complexity regularizer `Complexity(F_θ)`,

```text
    θ* = argmin_θ  Σ_i d(F_θ(x_i), L_i)  +  λ · Complexity(F_θ)
```

Implementation lives in `backend/src/simulation/search_engine.SearchEngine.fit`. Notes:
- `d(F_θ(x_i), L_i)` means: run the preprocessed audio through the family, get a contour, align and compare to the target contour.
- `Σ_i` is over the training slice of `PairedExample` rows.
- `λ` is a scalar regularization weight set in the search config, not hard-coded.
- `Complexity(F_θ)` is the family's declared simplicity penalty — typically derived from parameter count plus an MDL-ish term.

### 9.2 Shape distances

Three metrics, all returning a single float, all taking `(N, 2) float64` contours in the unit square:

| Metric                 | Module                              | Properties                                              |
|------------------------|-------------------------------------|---------------------------------------------------------|
| `procrustes_distance`  | `simulation/shape_distance.py`      | Full-Procrustes after optimal similarity alignment. Rotation/scale/translation invariant. Default fitness. |
| `frechet_distance`     | `simulation/shape_distance.py`      | Discrete Fréchet. Order-sensitive (preserves stroke direction). |
| `chamfer_distance`     | `simulation/shape_distance.py`      | Symmetric Chamfer. Order-invariant. Robust to sampling irregularities. |

**Never compare contours with `==` or naive per-point distance.** The contours will have different parameterizations even when they represent the same shape.

### 9.3 Audio preprocessing

```text
    raw .m4a file (AAC-in-MP4 from user recording)
      → decode via librosa.load(sr=None) → audioread → ffmpeg
      → validate duration ∈ [1.0, 3.0] s, peak ≤ -1 dBFS   (see docs/recording_protocol.md §3)
      → resample to config.audio_sample_rate_hz (default 16000)
      → loudness-normalize to -23 LUFS via pyloudnorm (ITU-R BS.1770)
      → VAD trim leading/trailing silence
      → frame into (num_frames, frame_length) with hop=config.audio_hop_length_samples
      → return ndarray float64 in [-1, 1]
```

Implementation in `backend/src/simulation/audio_preprocessor.AudioPreprocessor.load`. The full server flow (including file-on-disk side-effects during upload) is spelled out in `docs/recording_protocol.md` §7.

### 9.4 Glyph extraction

```text
    letter string  (e.g. "א")
      → load font (config.font_file, default backend/data/fonts/StamAshkenazCLM.ttf — Culmus, GPL v2)
      → render to config.glyph_raster_size_px square raster via freetype-py
      → binarize
      → cv2.findContours (external, CCOMP)
      → select largest contour (outer boundary)
      → resample to config.glyph_contour_num_points points (arc-length uniform)
      → center at centroid
      → scale into [-0.5, 0.5]
      → return ndarray (N, 2) float64
```

Implementation in `backend/src/simulation/glyph_extractor.GlyphExtractor.extract`.

---

## 10. Screen / module / endpoint inventory

### Phase 1 endpoints (FastAPI)

| Method | Path                     | Purpose                                                   |
|--------|--------------------------|-----------------------------------------------------------|
| GET    | `/health`                | Liveness/readiness; used by the Docker healthcheck        |
| POST   | `/api/datasets/audio`    | Upload a WAV/FLAC file + metadata; registers an AudioSample |
| POST   | `/api/datasets/glyphs`   | Render and store a GlyphTarget for a given letter         |
| POST   | `/api/datasets/pairs`    | Associate AudioSample + GlyphTarget into a PairedExample  |
| GET    | `/api/datasets/pairs`    | List paired examples; supports `split` + pagination query |

### Phase 2 additions (NOT in Phase 1)

| Method | Path                          | Purpose                                              |
|--------|-------------------------------|------------------------------------------------------|
| POST   | `/api/experiments`            | Start a new transform-family search                  |
| GET    | `/api/experiments`            | List runs                                            |
| GET    | `/api/experiments/{id}`       | Fetch a run + its best candidate                     |
| POST   | `/api/inference`              | One-shot inference: given audio + candidate, score   |

### Phase 4 additions (NOT in Phase 1)

| Kind | Path            | Purpose                                                   |
|------|-----------------|-----------------------------------------------------------|
| WS   | `/ws/live`      | Live pronunciation loop; MessagePack binary frames        |

---

## 11. Directory Structure & Key Entrypoints

```text
audio-glyph-inference/
├── AGENTS.md                              ← You are here
├── README.md
├── docker-compose.yml                     postgres + redis + backend (+ frontend in P4)
├── run_audio_glyph_inference.{sh,bat}     [k]/[q]/[v]/[r] launcher
├── .env                                   Ports + credentials (defaults)
├── .gitignore
├── .gitlab-ci.yml                         CI pipeline (lint → test → build → docker → release)
├── .codex/
│   ├── settings.json                      SessionStart / PreToolUse / PostToolUse / PreCompact / Stop hooks + permissions
│   ├── commands/
│   │   ├── scaffold.md                    /scaffold — scaffold a new module/family/model (signatures only)
│   │   ├── review.md                      /review  — deep review of changed code; reports only
│   │   ├── pre-commit.md                  /pre-commit — read-only audit; never stages or commits
│   │   ├── validate.md                    /validate — domain correctness check on simulation code
│   │   ├── phase-status.md                /phase-status — cross-phase progress report
│   │   └── new-transform-family.md        /new-transform-family — scaffold a new F_θ family module
│   └── skills/
│       ├── phase-awareness/SKILL.md       Session-start phase scoping
│       ├── transform-protocol/SKILL.md    TransformFamily contract enforcement
│       ├── data-driven-check/SKILL.md     No hard-coded domain values
│       ├── validation-protocol/SKILL.md   Reference-value tests, no mocking of core math
│       └── frontend-protocol/SKILL.md     Phase 4+ frontend rules (R3F disposal, Zustand, WS binary)
├── docs/
│   ├── AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md    Authoritative plan; Mermaid diagrams; gate checklists
│   ├── status.md                          Current phase + next actions
│   ├── versions.md                        Semver changelog
│   ├── run_guide.md                       How to run locally
│   ├── dependencies.md                    Why each dep was picked
│   ├── recording_protocol.md              How audio samples are recorded + uploaded + validated
│   └── phases/
│       ├── phase-1-plan.md
│       ├── phase-2-plan.md
│       ├── phase-3-plan.md
│       ├── phase-4-plan.md
│       └── phase-5-plan.md
└── backend/
    ├── Dockerfile                         python:3.11-slim + uv + libsndfile1 + libgl1
    ├── .dockerignore
    ├── pyproject.toml                     uv-managed; ruff config; pytest 100% coverage gate
    ├── data/
    │   ├── fonts/                         StamAshkenazCLM.ttf + LICENSE (Culmus, GPL v2, committed)
    │   ├── audio/                         Raw audio (not committed)
    │   └── contours/                      Extracted glyph contours as .npy
    ├── experiments/                       Experiment tracker JSONL output
    ├── src/
    │   ├── __init__.py
    │   ├── constants.py                   Hebrew letters + mathematical constants ONLY
    │   ├── config.py                      BackendSettings (Pydantic Settings, env-driven)
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── main.py                    FastAPI app factory (create_app + app)
    │   │   └── routers/
    │   │       ├── __init__.py
    │   │       ├── health.py               /health
    │   │       ├── datasets.py             /api/datasets/*
    │   │       ├── experiments.py          /api/experiments/* (Phase 2)
    │   │       ├── inference.py            /api/inference (Phase 2)
    │   │       └── live.py                 /ws/live (Phase 4)
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── audio_sample.py             AudioSample
    │   │   ├── glyph_target.py             GlyphTarget
    │   │   ├── paired_example.py           PairedExample
    │   │   ├── transform_candidate.py      TransformCandidate
    │   │   └── experiment_run.py           ExperimentRun
    │   ├── simulation/
    │   │   ├── __init__.py
    │   │   ├── audio_preprocessor.py       AudioPreprocessor
    │   │   ├── glyph_extractor.py          GlyphExtractor
    │   │   ├── shape_distance.py           procrustes / frechet / chamfer
    │   │   ├── search_engine.py            SearchEngine (Phase 2)
    │   │   ├── experiment_tracker.py       ExperimentTracker
    │   │   └── transforms/
    │   │       ├── __init__.py
    │   │       ├── transform_base.py       TransformFamily protocol
    │   │       ├── fourier_series.py       FourierSeriesFamily       (Phase 2)
    │   │       ├── lissajous.py            LissajousFamily           (Phase 2)
    │   │       ├── phase_space_embedding.py PhaseSpaceEmbeddingFamily (Phase 2)
    │   │       ├── dynamical_system.py     DynamicalSystemFamily     (Phase 3)
    │   │       └── symbolic_regression.py  SymbolicRegressionFamily  (Phase 3)
    │   └── data/
    │       ├── __init__.py
    │       ├── database.py                  Async engine + session factory
    │       └── orm/
    │           ├── __init__.py
    │           ├── base.py                   DeclarativeBase
    │           ├── audio_sample_row.py
    │           ├── glyph_target_row.py
    │           ├── paired_example_row.py
    │           ├── transform_candidate_row.py
    │           └── experiment_run_row.py
    └── tests/                               Mirrors src/, 100% coverage gate in CI
```

**Frontend directory:** intentionally absent until Phase 4. Do NOT create empty placeholder files for it.

---

## 12. Local Commands

### With Docker (primary)

```bash
./run_audio_glyph_inference.sh       # macOS/Linux — builds + starts, shows [k][q][v][r] menu
run_audio_glyph_inference.bat        # Windows equivalent
docker compose logs -f backend       # tail backend logs
docker compose exec backend bash     # shell into the backend container
```

### Without Docker (backend only — useful for TDD loops)

```bash
cd backend
uv venv
uv pip install -e '.[dev]'
uv run uvicorn src.api.main:app --reload --port 8000

# Tests
uv run pytest
uv run pytest tests/simulation/transforms/  # subset
uv run pytest -k fourier                    # keyword filter

# Lint + format
uv run ruff check .
uv run ruff format .

# Build (sdist + wheel)
uv build
```

Postgres and Redis must be running elsewhere when testing without Docker; point `BACKEND_DATABASE_URL` and `BACKEND_REDIS_URL` at them.

---

## 13. Testing Requirements

Testing is **mandatory** and enforced in CI. `backend/tests/` mirrors `backend/src/` — every module has a matching test file.

### Must be tested

- **All `simulation/*.py` modules** — audio preprocessor, glyph extractor, shape distance metrics, search engine, experiment tracker, every transform family.
- **All `models/*.py` modules** — round-trip Pydantic serialization and field validation.
- **All `data/orm/*.py` modules** — ORM row round-trip through a real Postgres via test container.
- **All API endpoints** — integration tests using `httpx.AsyncClient` against a real FastAPI app bound to a real Postgres.
- **`constants.py`** — the Hebrew letter list is exactly 22 long, in canonical order, no duplicates.
- **`config.py`** — env override behavior.

### Tooling

- `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`) + `pytest-cov`.
- `pytest-mock` is in the dev group but is **only** for mocking true external seams (an outbound HTTP dataset fetcher, for example). It is never used for core math or the database.
- `np.testing.assert_allclose(actual, expected, atol=..., rtol=...)` for every float comparison. Never `==`.
- `@pytest.mark.parametrize` for every letter when exercising the end-to-end pipeline.

### Rules (from global AGENTS.md §7 plus project additions)

- **No mocking of core math.** The Procrustes distance is computed against a real pair of arrays. The Fourier family's forward pass is computed against a real audio frame. If the test mocks these, it tests nothing.
- **No mocking of the database.** Integration tests spin up a real Postgres via a test container.
- **Reference-value tests are mandatory.** Every transform family has at least one test against a closed-form case (e.g., a pure-tone sine into the Lissajous family produces an ellipse with known axis ratio). A test that asserts the engine equals the engine is not a test.
- **Cross-speaker generalization is tested explicitly.** At least one test in Phase 2+ validates a candidate transform on a held-out speaker.
- **Coverage gate: 100%.** Enforced by `--cov-fail-under=100` in `backend/pyproject.toml`. If coverage drops, add tests — never lower the threshold.

### Common pitfalls (from prior projects and carried forward)

- `pytest-asyncio` fixture leaks — make async fixtures yield-based so they clean up.
- Forgetting `asyncio_mode = "auto"` and wondering why every async test hangs.
- Writing Procrustes tests that look at raw Euclidean distances without rotation alignment — they will fail stochastically on anything rotated, which is the whole point of using Procrustes in the first place.
- Float comparison with `==`. Use `assert_allclose` with documented tolerance.
- `@pytest.mark.parametrize` with `list("אבגדה...")` — this works in Python 3 because strings are iterables of single characters, but be intentional about it.

---

## 14. Change Policy & Local Documentation

When you finish a non-trivial change, update these files in this order:

1. **`docs/status.md`** — reflect the new current state. This is a "live state" document, not a log. Rewrite the relevant sections.
2. **`docs/versions.md`** — append changes under the computed next version heading (or create the heading if it doesn't exist yet). **Never modify `backend/pyproject.toml`'s `version` field directly** — that's the release pipeline's job. You only document what the next version contains.
3. **`docs/run_guide.md`** — only if how-to-run changed.
4. **`docs/dependencies.md`** — when adding, removing, or upgrading a dependency, document what and why.
5. **`docs/phases/phase-{N}-plan.md`** — if task status changed within the phase.
6. **`docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md`** — only for architectural changes. Flag the change to the user first.

### Version bump rules (reminder)

**Pre-alpha convention:** this project stays on `0.0.x` until the Phase 1 data pipeline runs end-to-end on real data. Use **patch** bumps for incremental work during that period. `0.1.0` is reserved for the first version where `POST /api/datasets/audio` + glyph extraction work together on real data. `1.0.0` is reserved for when data contracts are locked.

During pre-alpha:
- Any incremental work (bug fix, new endpoint, new family stub, docs change) → **patch** (0.0.1 → 0.0.2)
- Data-contract change → still patch during pre-alpha, BUT ask first and update master plan §3 in the same version.

After `0.1.0`:
- Bug fix, style, docs-only → **patch** (0.1.0 → 0.1.1)
- New feature, new family, new endpoint → **minor** (0.1.0 → 0.2.0)
- Data-contract change, breaking API change → **major** (0.x.y → 1.0.0) — **ask first**

Only one unreleased version at a time in `docs/versions.md`. If `0.0.2` is already in the file as unreleased, new work goes under `0.0.2` as a subsection, not under a new `0.0.3` heading.

---

## 15. Empty State & Onboarding

On a clean clone:
1. The directory tree exists.
2. `docker compose up --build -d` succeeds.
3. Postgres and Redis come up healthy.
4. The backend starts and `curl localhost:8000/health` returns 200 — **once** `src/api/main.py` is actually implemented. Until then, the container exits because `create_app()` raises `NotImplementedError`. That's expected during scaffold-only state.
5. The dataset endpoints return empty lists.
6. The font file is not yet in `backend/data/fonts/` — place it before running the glyph ingestion pipeline.

---

## 16. Phase 1 Completion Gate

Phase 1 is done when:

**Functional**
- [ ] `POST /api/datasets/audio` ingests a WAV file and registers an `AudioSample`
- [ ] `POST /api/datasets/glyphs` renders every Hebrew letter from the STAM font and stores a `GlyphTarget` + `.npy` contour
- [ ] `POST /api/datasets/pairs` associates rows into a `PairedExample`
- [ ] `GET /api/datasets/pairs?split=train` returns paginated paired examples
- [ ] `AudioPreprocessor.load` returns `(num_frames, frame_length) float64` in `[-1, 1]`
- [ ] `GlyphExtractor.extract` returns `(num_points, 2) float64` in the unit square for all 22 letters

**Infrastructure**
- [ ] `Dockerfile` builds cleanly; all scientific Python wheels load at import time
- [ ] `docker compose up --build -d` brings up postgres + redis + backend with all healthchecks green
- [ ] `run_audio_glyph_inference.{sh,bat}` launchers work end to end with the `[k]/[q]/[v]/[r]` loop
- [ ] `.env` has all Phase 1 variables with documented defaults
- [ ] `.gitlab-ci.yml` pipeline runs lint → test → coverage gate (100%) → build → docker-build green
- [ ] `backend/tests/` has a matching test file for every implemented module
- [ ] All `docs/` files are current (status, versions, run_guide, dependencies, phase-1-plan)

**Non-functional**
- [ ] Ruff clean (`ruff check .` + `ruff format --check .`)
- [ ] No hard-coded domain values outside `constants.py` / `config.py`
- [ ] No `# TODO` without a linked task
- [ ] No dead code, no commented-out blocks
- [ ] Every new function has full type annotations and an array shape/dtype/unit docstring line where applicable

---

## 17. Phase Transition Strategy

Each phase adds, never rewrites.

- **P1 → P2.** The data pipeline and schema stay. Phase 2 adds `SearchEngine` logic, concrete transform family `forward()` implementations, shape-distance bodies, experiment-tracker internals, and the `/api/experiments` + `/api/inference` routers. `docker-compose.yml` is unchanged.
- **P2 → P3.** Baseline families stay. Phase 3 adds `dynamical_system.py` and `symbolic_regression.py` as additional families behind the `[symbolic]` extra for PySR. `SearchEngine` gains a `bayesian` and `symbolic-regression` strategy. The eval harness gains cross-speaker splits.
- **P3 → P4.** Scaffold the `frontend/` directory (this is the first time it exists on disk). Add the `frontend` service to `docker-compose.yml` with `depends_on: { backend: { condition: service_healthy } }`. Implement `src/api/routers/live.py` with the WebSocket protocol. Backend code paths used by the live loop must be synchronous-safe for binary streaming. No existing Phase 1–3 code is rewritten.
- **P4 → P5.** No new production code. Writeup, analysis notebooks, per-family leaderboards. Uses the existing experiment tracker data.

---

## 18. Output & Completion Expectations

When you finish a non-trivial task, your final response MUST include a self-audit:

1. **Summary** — one or two sentences: what changed and why.
2. **Reuse check** — confirm you searched for existing helpers before writing new ones. Name the files you grep'd.
3. **Tech-debt check** — no shortcuts, no `Any`, no dead code, no duplicated logic, no vague names, no TODOs without tasks.
4. **File-organization check** — one concept per file. No god files created or expanded.
5. **Data-contract check** — no Pydantic model or ORM row changed without an architectural decision noted.
6. **Data-driven check** — no hard-coded domain literals added outside `constants.py` / `config.py`.
7. **Transform-protocol check** — if a transform family file was touched, the protocol invariants still hold.
8. **Docs check** — list every `docs/` file updated (status.md at minimum for non-trivial work; versions.md if it's a landable change).
9. **Test check** — list tests added/changed. State current coverage if available.
10. **Phase-scope check** — confirm the change lands inside the current phase's scope.
11. **Git state** — list files changed. **Suggest** a commit message (subject + body). Do NOT run any mutating git command — see §19.

If any item fails, say so explicitly. Do not paper over a failure.

---

## 19. Hands Off Git

**The user manages all git state themselves.** Carried from global AGENTS.md §10, reproduced here because it's project-load-bearing:

- Read-only git is fine: `git status`, `git diff`, `git log`, `git show`, `git blame`, `git branch --list`.
- **Everything that mutates repo state is forbidden:** `git add`, `git commit`, `git push`, `git pull`, `git checkout`, `git switch`, `git merge`, `git rebase`, `git cherry-pick`, `git reset`, `git restore`, `git stash`, `git tag`, `git branch` (mutating), `git clean`, `git config`. Also forbidden: `gh` commands that mutate state.
- When you think a commit should happen, **tell the user** and stop. Report what files changed, whether they should be one commit or several, and a *suggested* commit message clearly labeled as a suggestion.
- The `.codex/settings.json` Stop hook emits a reminder if uncommitted changes exist at turn end. That reminder is for the user, not for you.

---

## 20. Closing reminder

**Before the next change, re-read this file in full. Then re-read `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md`. Then `docs/status.md`. Then `docs/phases/phase-{N}-plan.md`. Then the source files you plan to touch. Only then implement.**

The unknown is the transformation. Everything else is scaffolding around that research question — keep it simple, keep it honest, keep it reproducible.