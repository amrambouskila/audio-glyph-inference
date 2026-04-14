# Run Guide

## Local, with Docker (primary)

```bash
./run_audio_glyph_inference.sh        # macOS / Linux
run_audio_glyph_inference.bat         # Windows
```

The launcher:
1. Runs `docker compose -f docker-compose.yml up --build -d`
2. Polls `http://localhost:8000/health` until the backend is ready
3. Prints a "services running" block with clickable URLs
4. Drops into the `[k] [q] [v] [r]` shutdown/restart loop

### The shutdown/restart menu

| Key | Action |
|-----|--------|
| `k` | Stop containers, keep images. Fast next restart. |
| `q` | Stop + remove project images. Keep volumes. |
| `v` | Stop + remove images + remove volumes. Full wipe. |
| `r` | Full restart (stop, remove images, rebuild, relaunch). Repeatable. |

Any unrecognized input reprints the menu — it does NOT exit.

## Ports

Overridable via `.env` at the project root. Defaults:

| Service  | Port |
|----------|------|
| backend  | 8000 |
| postgres | 5432 |
| redis    | 6379 |

## Local, without Docker (backend only)

```bash
cd backend
uv venv
uv pip install -e '.[dev]'
uv run uvicorn src.api.main:app --reload --port 8000
```

Postgres and Redis must be running elsewhere; point `BACKEND_DATABASE_URL` / `BACKEND_REDIS_URL` at them.

## Tests

```bash
cd backend
uv run pytest                    # 100% coverage gate enforced
uv run ruff check .
uv run ruff format --check .
```

## API docs

`http://localhost:8000/docs` — FastAPI auto-generated OpenAPI UI.
`http://localhost:8000/openapi.json` — raw schema.

## Observability

Phase 1: logs only. `docker compose logs -f backend` streams the uvicorn log.
Phase 4+: instrumentation TBD — update this section when it lands.