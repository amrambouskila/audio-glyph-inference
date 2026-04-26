---
name: review
description: Deep review of changed code against audio-glyph-inference standards — fix nothing, only report
---

# Review

Review changed code against project standards. **Fix nothing. Report only.**

## Before anything else

Re-read `AGENTS.md`, `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md`, and `docs/status.md`.

## Steps

1. Run `git diff --name-only` (read-only) to list changed files.
2. Read each changed file in full.
3. For each file, check:
   - **Type safety** — full annotations, no `Any`, no `# type: ignore` without reason
   - **One concept per file** — if a file now holds two unrelated concepts, flag split
   - **Data-driven** — no hard-coded domain numbers outside `src/constants.py` / `src/config.py`
   - **Docstrings** — shape/dtype/units line on every array-taking function
   - **Reuse** — was there an existing helper that should have been called? Grep for it and cite
   - **No Python loops in hot paths** — simulation code must vectorize or `@numba.jit`
   - **Sacred contracts** — if a Pydantic model changed, did the ORM row and docs/§3 change with it?
   - **Transform family contract** — if a transform was touched, does `forward()` still return `(N,2)` float64 unit-square?
   - **Tests** — is there a matching test file with coverage of new lines?
   - **No mocking of core math or the database**
   - **No dead code, no `# TODO` without linked task, no commented-out blocks**

## Report format

```
=== REVIEW REPORT ===

CRITICAL (must fix before merge):
- [file:line] issue

SHOULD-FIX:
- [file:line] issue

MINOR / STYLE:
- [file:line] issue

POSITIVE PATTERNS:
- what was done well

VERDICT: APPROVED / CHANGES REQUESTED
```