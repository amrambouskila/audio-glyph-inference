---
name: phase-status
description: Assess progress across the 5-phase roadmap and produce a status table + next-action list
---

# Phase Status

Assess the project's progress across all 5 phases and report a status table plus the next concrete action.

## Before anything else

Read `AGENTS.md`, `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md`, `docs/status.md`, every file in `docs/phases/`.

## Steps

1. For each phase, walk its gate checklist from `docs/phases/phase-N-plan.md` and mark each item DONE / IN-PROGRESS / PENDING based on what's actually on disk (read the code, don't guess).
2. Identify the current phase (the first one that is not fully DONE).
3. List the next 3 concrete actions for the current phase.

## Report

```
=== PHASE STATUS ===

Phase 1 — Data Pipeline              : DONE / IN-PROGRESS (x/y) / PENDING
Phase 2 — Baseline Transform Search  : ...
Phase 3 — Expanded Search Space      : ...
Phase 4 — Live Pronunciation UI      : ...
Phase 5 — Writeup & Negative Results : ...

Current phase: N
Current gate items remaining:
    - item 1
    - item 2

Next 3 actions:
    1. <file> — <what to do>
    2. ...
    3. ...
```

Do NOT start implementing. Report only.