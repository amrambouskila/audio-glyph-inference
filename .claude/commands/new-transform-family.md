---
name: new-transform-family
description: Scaffold a new transform family module with protocol conformance, tests, and docs entry
---

# New Transform Family

Scaffold a new `TransformFamily` implementation. Signatures and tests only — no logic.

## Before anything else

1. Re-read `CLAUDE.md`.
2. Read `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md` §4 (transform search space).
3. Read `backend/src/simulation/transforms/transform_base.py` to confirm the protocol is still current.
4. Grep `backend/src/simulation/transforms/` for existing families — do NOT duplicate.

## What to produce

- `backend/src/simulation/transforms/<snake_name>.py`
  - Class implementing `TransformFamily`
  - `name()` returns a unique family string
  - `parameter_space()` returns the full θ bounds
  - `forward(audio, theta)` raises `NotImplementedError`
  - Docstring at module + class level describing the mathematical form in LaTeX and the physical/geometric intuition
- `backend/tests/simulation/transforms/test_<snake_name>.py`
  - Imports the family
  - One skipped test per method
  - One skipped test asserting `forward()` output shape `(N, 2)` dtype `float64` unit-square
- Append a row to the transform-family table in `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md` §4

## Report

- List every file created
- Quote the mathematical form of the new family (from the docstring) for the user to approve
- State the next step: "Implement `forward()` — then run `/validate`"