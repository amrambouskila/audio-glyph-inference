# Dependencies

Every third-party package in `backend/pyproject.toml` and `frontend/package.json` is here with *why*. When adding, removing, or upgrading, update this file. See global `CLAUDE.md` §5 for the hard-constraint stack rules.

## Web / API

| Package | Why |
|---------|-----|
| `fastapi` | Default Python API framework per global `CLAUDE.md` §5. Async, WebSocket-ready for Phase 4. |
| `uvicorn[standard]` | ASGI server per global `CLAUDE.md` §5. |
| `websockets` | Raw websockets used by FastAPI under the hood and by any future client test code. |
| `python-multipart` | Required by FastAPI for multipart file uploads (audio sample ingestion). |

## Data validation

| Package | Why |
|---------|-----|
| `pydantic>=2.6.0` | v2 is the default for every API contract, config schema, and data model per global `CLAUDE.md` §5. |
| `pydantic-settings` | Environment-driven config (`src/config.BackendSettings`). Replaces ad-hoc `os.environ` reads. |

## Database

| Package | Why |
|---------|-----|
| `sqlalchemy[asyncio]>=2.0.27` | Default ORM per global `CLAUDE.md` §5. SQLAlchemy owns the DB layer; Pydantic owns API. Pulls `greenlet` (its async bridge) — also why `[tool.coverage.run]` sets `concurrency = ["thread", "greenlet"]` so async post-await lines are traced. |
| `asyncpg` | Default async Postgres driver per global `CLAUDE.md` §5 (never `psycopg2` for new work). |
| `alembic` | Migrations. Schema changes land as alembic revisions, not hand-edited DDL. |

## Cache

| Package | Why |
|---------|-----|
| `redis[hiredis]` | Default cache / pubsub. Phase 4 uses Redis pubsub to broadcast inference results across backend workers. |

## Numerical / scientific

| Package | Why |
|---------|-----|
| `numpy` | Universal. Every array in simulation is `ndarray` with explicit dtype. |
| `scipy` | Solvers (`scipy.optimize` for CMA-ES-adjacent work), spatial (`scipy.spatial.cKDTree` — NEVER `KDTree`), signal (`scipy.signal` for filtering). |
| `pandas` | Default DataFrame library per global `CLAUDE.md` §5. Used for experiment logs, eval tables, and notebook analysis. **Not polars.** |
| `numba` | JIT for hot loops that can't be vectorized in NumPy (ODE integration inside transforms, per-frame scoring). |
| `cma` | pycma (BSD-3, pure-Python) implements the Phase-2 `cma-es` search strategy with explicit seed control and stable normalized-genotype options. SciPy does not provide a CMA-ES implementation with this API. |

The in-repo Phase-3 Bayesian optimizer also uses `scipy.special.ndtr` for the expected-improvement acquisition; no additional optimizer dependency is required.

## Audio

| Package | Why |
|---------|-----|
| `librosa` | Default audio preprocessing (load, resample, MFCCs, framing). Thin wrapper over SciPy + soundfile with sensible defaults. |
| `soundfile` | Underlying audio I/O for librosa. libsndfile bindings. |
| `pyloudnorm` | Loudness normalization (ITU-R BS.1770) before framing — keeps gain consistent across recordings. |

## Glyph / contour

| Package | Why |
|---------|-----|
| `opencv-python-headless` | Contour extraction (`findContours`), resampling, raster ops. `headless` avoids dragging in GUI libs on the server image. |
| `shapely` | Polygon / curve manipulation (simplification, orientation fixing) in vectorized form. |
| `freetype-py` | Render glyphs directly from `.ttf`/`.otf` files; lets us access the STAM-style Torah font at the raster level without a browser or Cairo. |
| `pillow` | Intermediate raster buffer for the glyph pipeline. Minimal — only used when freetype hands us pixel data. |

## Deep learning

| Package | Why |
|---------|-----|
| `torch` | Default DL framework per global `CLAUDE.md` §5. Used in Phase 3+ for any learned feature extraction, and for gradient-based parameter search in transform families when analytic gradients are available. Pinned to the CPU wheel index via `[tool.uv.sources]` → `download.pytorch.org/whl/cpu` (CPU-only project; avoids the multi-GB CUDA build); the Dockerfile install step passes the same `--extra-index-url` so the pinned `+cpu` wheels are locatable. |
| `torchaudio` | PyTorch-native audio ops (used where librosa would be slower, e.g. in-batch mel spectrogram extraction). |

## Visualization (static)

| Package | Why |
|---------|-----|
| `matplotlib` | Default static plotting per global `CLAUDE.md` §5. Training curves, per-letter shape plots, diagnostic figures. |
| `seaborn` | Statistical overlay on matplotlib. Default for analysis notebooks in Phase 5. |

## Tracking & serialization

| Package | Why |
|---------|-----|
| `rich` | Pretty-printed experiment run summaries in the CLI tracker. |
| `msgpack` | Binary serialization for WebSocket payloads (Phase 4). JSON is only used for metadata. |
| `httpx` | Default HTTP client per global `CLAUDE.md` §5 — used as the async test client (`httpx.AsyncClient`) for FastAPI integration tests. No external dataset fetching (master plan §11.1). |

## Version floors and the lock

`backend/uv.lock` is the resolved, committed dependency set. Since the `lint` / `sast` / `test` CI jobs
install with `uv sync --locked`, the lock is load-bearing: **any edit to `backend/pyproject.toml` must be
followed by `uv lock`, and both files committed together**, or every job fails at install time.

The `sast` job audits the exported lock, so a new advisory against a pinned version turns the pipeline red
until the lock is refreshed. Remediate with a targeted `uv lock --upgrade-package <name>` rather than a
blanket `uv lock --upgrade`, which would also pull unrelated major bumps (librosa 1.x, opencv 5.x, redis 8.x)
into a project gated on 100% coverage of numerical code.

Five declared floors exist purely to keep a *fresh* resolve — `backend/Dockerfile` runs
`uv pip compile pyproject.toml` and never reads the lock — off a version with a known advisory:

| Package | Floor | Why the floor, not just the lock |
|---------|-------|----------------------------------|
| `python-multipart` | `>=0.0.31` | PYSEC-2026-3036/3037/3039/3040 |
| `pydantic-settings` | `>=2.14.2` | GHSA-4xgf-cpjx-pc3j |
| `pillow` | `>=12.3.0` | 13 advisories against 12.2.0 (PYSEC-2026-2253..3496) |
| `msgpack` | `>=1.2.1` | PYSEC-2026-3625 |
| `torch` | `>=2.13.0` | torch 2.12 and below cap the transitive `setuptools` below 83.0.0, pinning it onto PYSEC-2026-3447 |

`torchaudio` stays at `>=2.2.0` deliberately: 2.11.0 is the newest published build on
`download.pytorch.org/whl/cpu` and it declares no `torch` pin, so raising it to match `torch` would make the
resolve unsatisfiable. Neither package is imported anywhere in `src/`, `tests/`, or `scripts/` today.

## Optional extras

| Extra      | Package | Why |
|------------|---------|-----|
| `symbolic` | `pysr` | Symbolic regression family — deferred to Phase 3 because it drags in a Julia runtime. Installed only when Phase 3 work begins. |
| `symbolic` | `sympy` | Required by PySR for expression manipulation. |

Note: the `symbolic` extra now backs the implemented Phase-3 PySR proposal/search path; it remains optional because
saved symbolic candidates can be evaluated without Julia/PySR installed.

## Frontend runtime

| Package | Why |
|---------|-----|
| `react` / `react-dom` | Phase-4 browser UI runtime. |
| `vite` | Frontend dev server and production bundler. |
| `typescript` | Strict frontend typing. |
| `zustand` | Small serializable UI/live-state store; no Three.js objects are stored in it. |
| `@react-three/fiber` / `@react-three/drei` / `three` | R3F contour overlay for target and generated glyph geometry. |
| `chart.js` / `react-chartjs-2` | Live shape-distance history dashboard. |
| `@msgpack/msgpack` | Binary WebSocket frame encoding/decoding for the Phase-4 live loop. |
| `lucide-react` | Consistent icon buttons for toolbar controls. |

## Frontend dev

| Package | Why |
|---------|-----|
| `@vitejs/plugin-react` | React Fast Refresh and Vite JSX transform. |
| `eslint` / `@eslint/js` / `typescript-eslint` | Frontend lint gate. |
| `eslint-plugin-react-hooks` / `eslint-plugin-react-refresh` | React hook and Fast Refresh correctness checks. |
| `vitest` / `@vitest/coverage-v8` | Frontend unit-test runner and coverage gate for utility and focused component behavior. |
| `@testing-library/react` / `@testing-library/jest-dom` / `jsdom` | DOM-oriented frontend tests. |
| `@types/react` / `@types/react-dom` | React TypeScript declarations. |
| `@playwright/test` | Real-browser frontend smoke tests for the Phase-4 live UI, including R3F canvas rendering across desktop/mobile Chromium. |
| `pngjs` / `@types/pngjs` | Decode Playwright canvas screenshots for deterministic nonblank pixel assertions. |

## Dev group

| Package | Why |
|---------|-----|
| `pytest` | Default test runner per global `CLAUDE.md` §5. |
| `pytest-asyncio` | Required for async FastAPI + SQLAlchemy tests (`asyncio_mode = "auto"`). |
| `pytest-cov` | Coverage gate enforcement (`--cov-fail-under=100`). |
| `pytest-mock` | Used ONLY for non-core seams (e.g. HTTP clients at the boundary). Never for core math or the database. |
| `ruff` | Default lint + format. Replaces black, isort, flake8, pylint per global `CLAUDE.md` §5. |
| `testcontainers[postgres]` | Spins a disposable real Postgres for integration tests when `BACKEND_DATABASE_URL` is unset (local `uv run pytest`); CI uses its `services: postgres` instead. Real DB, never mocked (CLAUDE.md §13). |
