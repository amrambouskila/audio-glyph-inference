# Run Guide

## Local, with Docker (primary)

```bash
./run_audio_glyph_inference.sh        # macOS / Linux
run_audio_glyph_inference.bat         # Windows
```

The launcher:
1. Runs `docker compose -f docker-compose.yml up --build -d`
2. Polls `http://localhost:8220/health` until the backend is ready
3. Prints a "services running" block with the frontend, backend health, API docs, and OpenAPI URLs
4. Drops into the `[k] [q] [v] [r]` shutdown/restart loop

### The shutdown/restart menu

| Key | Action |
|-----|--------|
| `k` | Stop containers, keep images. Fast next restart. |
| `q` | Stop + remove project images. Keep volumes. |
| `v` | Stop + remove images + remove volumes. Full wipe. |
| `r` | Full restart (stop, rebuild, relaunch; images kept). Repeatable. |

Any unrecognized input reprints the menu — it does NOT exit.

## Ports

Overridable via `.env` at the project root (copy `.env.example` and edit). Defaults:

| Service  | Port |
|----------|------|
| frontend | 5220 |
| backend  | 8220 |
| postgres | 5520 |
| redis    | 6520 |

## Local, without Docker

### Backend

```bash
cd backend
uv venv
uv pip install -e '.[dev]'
uv run uvicorn src.api.main:app --reload --port 8220
```

Postgres and Redis must be running elsewhere; point `BACKEND_DATABASE_URL` / `BACKEND_REDIS_URL` at them.

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

The browser app reads `VITE_API_BASE_URL`, `VITE_WS_URL`, and `VITE_AUDIO_SAMPLE_RATE_HZ` from the environment. Defaults match `.env.example`.
The live UI loads stored glyph targets from `GET /api/datasets/glyphs` and recent completed-run best candidates from the experiment endpoints; the ID fields also accept manual UUID entry.

### Stage-7 dataset audit

Before running real Phase-2/3 searches, verify the uploaded Stage-7 dataset is complete:

```bash
cd backend
uv run python scripts/audit_stage7_dataset.py --manifest experiments/manifests/phase5_pending_real_data.json
```

The command exits non-zero until all planned audio takes, glyph targets, and pair rows exist. Use `--format json` for a machine-readable report.

### Live UI smoke data

On a fresh database, the live UI has no glyph targets or completed-run candidates to select. To seed deterministic non-empirical rows for browser round-trip testing:

```bash
docker compose exec backend python scripts/seed_live_smoke.py
```

This creates catalog-visible glyph targets for all 27 glyph forms plus one completed `lissajous` smoke run/candidate. It is not a fitted research result and does not satisfy the Phase-2/3 empirical gates.

To verify the backend live WebSocket against every seeded glyph target before opening the browser:

```bash
docker compose exec backend python scripts/smoke_live_roundtrip.py
```

The command selects the latest completed run's best candidate, configures `/ws/live` once per Hebrew letter, sends one synthetic PCM16 frame, and fails if any glyph does not return a score.

### Browser live-loop evidence

The Phase-4/5 manual gate still requires testing all 27 glyph forms in the browser and confirming the visible score update rate stays at or above 10 Hz. After the browser pass, record the evidence as JSON and set `live_loop_evidence` in `backend/experiments/manifests/phase5_pending_real_data.json` to that file path before rendering the Phase-5 report.

The pending manifest also excludes the non-empirical `live-smoke-seed` run by name. Keep smoke-seed runs excluded from the Phase-5 report; remove or adjust `excluded_run_names` only for real experiment ledgers that should count as research evidence.

Generate a fillable all-glyph-form evidence template with:

```bash
cd backend
uv run python scripts/generate_live_loop_evidence_template.py --candidate-id <candidate-uuid> --browser "Chromium <version>" --score-rate-threshold-hz 10 --output experiments/live-loop-evidence.json
```

The generated file intentionally starts with `0` rates/update counts, blank glyph ids, and `false` visibility flags. Fill it with the observed browser values before pointing the manifest at it.

```json
{
  "tested_at": "2026-04-16T00:00:00Z",
  "browser": "Chromium 124",
  "candidate_id": "22222222-2222-2222-2222-222222222222",
  "score_rate_threshold_hz": 10.0,
  "score_rate_hz_by_letter": {"א": 12.5},
  "score_updates_by_letter": {"א": 25},
  "glyph_target_id_by_letter": {"א": "44444444-4444-4444-4444-444444444444"},
  "visible_score_by_letter": {"א": true}
}
```

The real file must include exactly every glyph form in `backend/src/constants.py::GLYPH_FORMS` for all four maps. The report renderer rejects missing forms, unknown forms, invisible scores, zero update counts, and score rates below the recorded threshold.

## Tests

```bash
cd backend
uv run pytest                    # 100% coverage gate enforced
uv run ruff check .
uv run ruff format --check .

cd ../frontend
npm run lint
npm run test
npx playwright install chromium   # first browser-test run only
npm run test:browser
npm run build
```

On Windows PowerShell, use `npm.cmd` for the frontend commands if the `npm.ps1` shim is blocked by execution policy.

## API docs

`http://localhost:5220` - live pronunciation UI.
`http://localhost:8220/docs` - FastAPI auto-generated OpenAPI UI.
`http://localhost:8220/openapi.json` - raw schema.

## Observability

Logs only. `docker compose logs -f backend` streams the uvicorn log; `docker compose logs -f frontend` streams nginx startup/runtime logs.
