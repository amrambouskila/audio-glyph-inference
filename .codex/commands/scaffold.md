---
name: scaffold
description: Scaffold a new module, transform family, Pydantic model, or API router with signatures, types, and tests — no logic
---

# Scaffold

Scaffold a new module following the audio-glyph-inference conventions. Signatures, type annotations, and empty test files only — **no logic**. Wait for the user to request implementation in a follow-up.

## Before anything else

1. Re-read `AGENTS.md` (project root) in full.
2. Read `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md`.
3. Read `docs/status.md` and `docs/versions.md`.
4. Grep for existing modules that already provide what you're about to create. If there's a match, STOP and report it instead of creating a new file.

## What to produce

Given the component type, create all associated files per the one-concept-per-file rule.

### New Pydantic model
- `backend/src/models/<snake_name>.py` — single `BaseModel` class with typed fields, no logic
- `backend/src/data/orm/<snake_name>_row.py` — matching SQLAlchemy `Base` subclass with `__tablename__`; columns declared to match the Pydantic fields 1:1
- `backend/tests/models/test_<snake_name>.py` — placeholder test file with imports + one skipped test stub

### New transform family
- `backend/src/simulation/transforms/<snake_name>.py` — class implementing `TransformFamily` protocol (`name`, `parameter_space`, `forward`). Methods raise `NotImplementedError`
- `backend/tests/simulation/transforms/test_<snake_name>.py` — one skipped test per method

### New FastAPI router
- `backend/src/api/routers/<resource>.py` — `APIRouter` symbol declared, endpoints TBD
- `backend/tests/api/test_<resource>.py` — placeholder with a skipped integration test

### New simulation engine
- `backend/src/simulation/<snake_name>.py` — class with type-annotated `__init__` and primary methods raising `NotImplementedError`
- `backend/tests/simulation/test_<snake_name>.py` — placeholder

## Rules

- Full type annotations on every signature. `ANN` ruff rules are on.
- Docstrings: one short line per function; for array-taking functions include shape / dtype / units on a second line.
- No hard-coded domain numbers — if you need a parameter, add it to `backend/src/config.BackendSettings` instead.
- Every new file must be added as a matching test file in the mirrored `backend/tests/` path.
- Do NOT implement behavior. Do NOT run tests yet. Do NOT edit unrelated files.

## Report

After scaffolding, print:
- Every file created (absolute paths)
- Every existing file touched (should be zero)
- The next concrete step the user should ask for (usually: implement `<method>` in `<file>`)