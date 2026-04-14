# Status

**Current phase:** Phase 1 — Data pipeline
**Current version (pyproject.toml):** 0.0.1
**Next computed version:** 0.0.2 (patch — pre-alpha: use patch bumps until 1.0.0 unless explicitly told otherwise)

## What was just built

Scaffold + data decisions only. No simulation logic yet.

- Directory tree, Docker stack, launcher scripts, `.claude/` wiring, project `CLAUDE.md`, master plan, and signature-only backend modules.
- **No simulation logic has been implemented.** Every method in `backend/src/simulation/` and `backend/src/data/` currently raises `NotImplementedError`.
- **Audio data source resolved** (master plan §11.1): user-uploaded `.m4a` files only, across the five accents `ashkenazi`, `sephardi`, `moroccan`, `yemenite`, `chabad`. No CLI recorder, no browser recorder, no public-dataset ingester.
- **Generalization-split policy resolved** (master plan §11.3): accent-disjoint splits; leave-one-accent-out evaluation (5 rows) is the headline metric.
- **Font resolved** (master plan §11.2): `StamAshkenazCLM.ttf` from the Culmus Project (GPL v2, Yoram Gnat via Maxim Iorsh's CLM packaging). Font file, LICENSE, and README live in `backend/data/fonts/`.
- `AudioSample` Pydantic model + ORM row annotated with the new `accent` field; `constants.ACCENTS` vocabulary added with all five accents.
- `librosa` + `audioread` (explicit dep) + ffmpeg (already in the backend image) handle `.m4a` decoding server-side at ingestion time.

## What's next (Phase 1 concrete actions)

**Read `docs/recording_protocol.md` before touching the ingestion code** — it locks the duration range, loudness target, articulation rule, on-disk layout, and server validation behavior that the router and preprocessor implement.

1. Implement `src/simulation/glyph_extractor.GlyphExtractor.extract` against `StamAshkenazCLM.ttf`. Validate visually against each of the 22 letters. (Starts decoupled — no DB, no API.)
2. Implement `src/simulation/audio_preprocessor.AudioPreprocessor.load` per `docs/recording_protocol.md` §7 (decode m4a → resample to 16 kHz → loudness-normalize to -23 LUFS → VAD trim → frame). Unit-tested without the router.
3. Wire `src/data/database.py` + alembic baseline migration for `audio_samples` (including `accent`), `glyph_targets`, `paired_examples`.
4. Implement `src/api/main.create_app`, `src/api/routers/health`, `src/api/routers/datasets`. `POST /api/datasets/audio` implements the validation + storage flow from `docs/recording_protocol.md` §7.
5. Commit one tiny test fixture `.m4a` at `backend/tests/fixtures/test-sample.m4a` (per `docs/recording_protocol.md` §8). Integration test uploads it and asserts the row lands.
6. First pytest run. Get to 100% coverage on whatever's implemented.
7. Record and upload the first batch: 5 repetitions × 22 letters × 5 accents = **550 m4a files**, per the session structure in `docs/recording_protocol.md` §4. Lock N after the first session.

## Open blockers

None.