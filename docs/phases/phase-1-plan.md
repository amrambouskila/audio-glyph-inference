# Phase 1 Plan — Data Pipeline

**Goal.** Build an end-to-end ingestion pipeline that turns (audio recording, Hebrew letter) and (font glyph, letter) into queryable `PairedExample` rows.

**Exit gate.** See master plan §9.

## In scope

- Audio ingestion (upload endpoint + optional public-dataset ingester)
- Audio preprocessing (resample → loudness-normalize → frame)
- Glyph rendering from STAM-style Torah font
- Contour extraction and normalization to unit square
- Postgres schema + alembic migration baseline
- Minimal FastAPI: `/health`, `POST /api/datasets/audio`, `POST /api/datasets/glyphs`, `POST /api/datasets/pairs`, `GET /api/datasets/pairs`
- Pytest suite with 100% line coverage across everything implemented
- `.gitlab-ci.yml` pipeline green

## Explicitly deferred

- Transform families beyond signature stubs
- SearchEngine logic
- Shape-distance metrics beyond signatures
- Any WebSocket
- Any frontend
- PySR / symbolic regression
- Any form of candidate ranking or experiment UI

## Tasks

1. ~~Decide audio data source~~ **DONE** — user-uploaded `.m4a` files, 5 accents (master plan §11.1).
2. ~~Place STAM Torah font~~ **DONE** — `StamAshkenazCLM.ttf` vendored under `backend/data/fonts/` (master plan §11.2).
3. ~~Recording protocol~~ **DONE** — see `docs/recording_protocol.md` for articulation rules, environment, timing, session structure, upload workflow, server validation flow, test fixture policy, and change-management rules. **Read this before touching the ingestion code.**
4. Implement `src/simulation/glyph_extractor.GlyphExtractor.extract` against `StamAshkenazCLM.ttf`. Visual validation for each of the 22 letters.
5. Implement `src/simulation/audio_preprocessor.AudioPreprocessor.load` — decode `.m4a` via `librosa.load` (which uses `audioread` → `ffmpeg` for AAC-in-MP4), resample to `config.audio_sample_rate_hz`, loudness-normalize to -23 LUFS (`pyloudnorm`), VAD trim, frame. Returns `(num_frames, frame_length) float64`. Validation rules are in `docs/recording_protocol.md` §3 + §7.
5. Implement `src/data/database` async engine + session factory.
7. Alembic init + first revision (`audio_samples` with `accent` column, `glyph_targets`, `paired_examples`).
8. Implement `src/api/main.create_app` wiring.
9. Implement `src/api/routers/health`.
10. Implement `src/api/routers/datasets` — validation + storage flow defined in `docs/recording_protocol.md` §7:
    - `POST /api/datasets/audio` — multipart `.m4a` upload + form fields `letter`, `accent`, `repetition`.
    - `POST /api/datasets/glyphs` — render + store a target glyph contour for one letter.
    - `POST /api/datasets/pairs` — associate `AudioSample` ↔ `GlyphTarget`.
    - `GET /api/datasets/pairs` — list paired examples (filter by `split`, `accent`, `letter`).
11. Commit tiny test fixture at `backend/tests/fixtures/test-sample.m4a` per `docs/recording_protocol.md` §8.
12. Tests for every module above. 100% coverage. Integration test uploads the fixture through the endpoint and verifies the row and file land correctly. **Do not mock the database or librosa decode** — use a real Postgres test container and the real ffmpeg decode path.
13. Alembic upgrade runs on backend container startup (migration stage added to entrypoint if needed).
14. GitLab CI pipeline green end-to-end.
15. **Record and upload the first batch** per `docs/recording_protocol.md` §4. Target: 5 repetitions × 22 letters × 5 accents = 550 m4a files.
16. Update `docs/status.md` and `docs/versions.md` per global CLAUDE.md §6.

## Acceptance criteria

- `curl -X POST -F 'file=@alef-ashkenazi-rep1.m4a' -F 'letter=א' -F 'accent=ashkenazi' -F 'repetition=1' http://localhost:8000/api/datasets/audio` returns an `AudioSample` JSON and the file lands under `backend/data/audio/ashkenazi/א/`.
- `curl -X POST 'http://localhost:8000/api/datasets/glyphs?letter=א'` returns a `GlyphTarget` JSON and a `.npy` contour lands in `backend/data/contours/`.
- `GET /api/datasets/pairs?split=train&accent=ashkenazi` returns a paginated list.
- `pytest` exits 0 with 100% coverage.
- `ruff check .` and `ruff format --check .` clean.
- GitLab CI: all stages green.