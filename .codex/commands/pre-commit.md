---
name: pre-commit
description: Read-only pre-commit audit — tests, lint, SAST, coverage, contracts, docs. Never stages or commits.
---

# Pre-Commit Audit

Run this before the user commits. **This command never stages or commits anything.** It only reports a verdict table so the user can decide whether the change is ready.

## Before anything else

Re-read `AGENTS.md`, `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md`, `docs/status.md`, `docs/versions.md`.

## Steps

1. **Tests**
   - Run `cd backend && uv run pytest` (or `python -m pytest` fallback).
   - Report pass/fail.
2. **Lint**
   - Run `cd backend && uv run ruff check .` and `uv run ruff format --check .`.
   - Report any findings.
3. **SAST**
   - Run `cd backend && uv run semgrep scan --config auto --error .`, then the exported-lock audit (`uv export --frozen --no-emit-project --no-hashes --all-groups --all-extras --no-emit-package torch --no-emit-package torchaudio -o requirements-audit.txt && uvx pip-audit --requirement requirements-audit.txt --no-deps`), `cd frontend && npm audit --audit-level=high`, and `gitleaks detect --no-git --redact` from the repo root.
   - Any HIGH/CRITICAL finding is a blocker. List MEDIUM findings with their inline justification; an unjustified MEDIUM is a blocker.
   - For every changed input boundary, confirm its row in `AGENTS.md` §13A `<security>` still describes the code (injection classes + defense); a new boundary without a row is a blocker.
4. **Coverage gate**
   - Verify `--cov-fail-under=100` still holds. If not, list uncovered lines.
5. **Contract integrity**
   - For each changed Pydantic model, confirm the matching ORM row was also updated.
   - For each changed transform family, confirm the protocol methods (`name`, `parameter_space`, `forward`) are still intact.
6. **Data-driven check**
   - Grep changed files for hard-coded numeric literals outside `constants.py` / `config.py`. Flag any hits.
7. **Docs**
   - Did any logic change land without an update to `docs/status.md`? Flag it.
   - Did `docs/versions.md` get a heading for the computed next version? Compute it from `backend/pyproject.toml`'s `version` field.
8. **Forward-compat**
   - Do any changes conflict with the next phase in the master plan?

## Report

```
=== PRE-COMMIT REPORT ===

Tests          : PASS / FAIL (N failed)
Lint           : PASS / FAIL
SAST           : CLEAN / FINDINGS (HIGH/CRITICAL: N; MEDIUM unjustified: N; boundaries undocumented: list)
Coverage       : N% (gate 100%)
Contracts      : OK / DRIFT (list files)
Data-driven    : OK / HARD-CODED (list file:line)
Docs           : CURRENT / MISSING (list files)
Forward-compat : OK / AT RISK (explain)

Changed files: N
Suggested commit message (SUGGESTION ONLY — user decides):
    <subject>

    <body>

VERDICT: READY TO COMMIT / NOT READY (list blockers)
```

**Do not run any mutating git command. Do not stage files. Do not commit.** The user manages git.