# audio-glyph-inference-backend

Backend package for the `audio-glyph-inference` project: FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + NumPy/SciPy + PyTorch, running on Python 3.11+.

Responsibilities:

- Ingest raw Hebrew-letter audio recordings and render canonical glyph contours from a STAM-style Torah font.
- Persist `AudioSample`, `GlyphTarget`, `PairedExample`, `TransformCandidate`, and `ExperimentRun` rows in Postgres.
- Host the `SearchEngine` and the `TransformFamily` zoo that fit an explicit, interpretable operator `F_θ : x(t) → G` from audio to 2D glyph geometry.
- Expose REST endpoints under `/api/datasets`, `/api/experiments`, `/api/inference`, plus a live WebSocket at `/ws/live` (Phase 4).

See the repository root `README.md` for the full project overview, architecture diagrams, and phase roadmap, and `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md` for the authoritative design document.
