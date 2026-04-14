# Dependencies

Every third-party package in `backend/pyproject.toml` is here with *why*. When adding, removing, or upgrading, update this file. See global `CLAUDE.md` §5 for the hard-constraint stack rules.

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
| `sqlalchemy[asyncio]>=2.0.27` | Default ORM per global `CLAUDE.md` §5. SQLAlchemy owns the DB layer; Pydantic owns API. |
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
| `torch` | Default DL framework per global `CLAUDE.md` §5. Used in Phase 3+ for any learned feature extraction, and for gradient-based parameter search in transform families when analytic gradients are available. |
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
| `httpx` | Default HTTP client (sync or async) per global `CLAUDE.md` §5 — used for any external dataset fetching. |

## Optional extras

| Extra      | Package | Why |
|------------|---------|-----|
| `symbolic` | `pysr` | Symbolic regression family — deferred to Phase 3 because it drags in a Julia runtime. Installed only when Phase 3 work begins. |
| `symbolic` | `sympy` | Required by PySR for expression manipulation. |

## Dev group

| Package | Why |
|---------|-----|
| `pytest` | Default test runner per global `CLAUDE.md` §5. |
| `pytest-asyncio` | Required for async FastAPI + SQLAlchemy tests (`asyncio_mode = "auto"`). |
| `pytest-cov` | Coverage gate enforcement (`--cov-fail-under=100`). |
| `pytest-mock` | Used ONLY for non-core seams (e.g. HTTP clients at the boundary). Never for core math or the database. |
| `ruff` | Default lint + format. Replaces black, isort, flake8, pylint per global `CLAUDE.md` §5. |