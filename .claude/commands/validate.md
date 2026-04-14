---
name: validate
description: Validate simulation code for correctness, interpretability, and data-driven compliance
---

# Validate

Multi-layer audit of simulation / transform / scoring code. This is the domain-specific sibling of `/review` — it checks whether the math itself holds up, not just whether the style is clean.

## Before anything else

Re-read `CLAUDE.md` and `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md` §4 (transform families) and §5 (scoring).

## Layers

### 1. Structural completeness
- Every transform family module implements the `TransformFamily` protocol completely
- `forward()` returns `ndarray` shape `(N, 2)`, dtype `float64`, unit-square coordinates
- `parameter_space()` returns every parameter used inside `forward()` — no undeclared θ

### 2. Numerical correctness
- No NaN/Inf can occur under the parameter bounds returned by `parameter_space()`. Trace through.
- No divide-by-zero. No `sqrt` of negatives. No log of zero.
- Dimensional sanity — the transform does not mix frequency-domain and time-domain values without an explicit FFT.

### 3. Data-driven compliance
- No hard-coded parameter values inside `forward()`. Every θ comes from the `theta` argument.
- No hard-coded audio sample rate, frame length, raster size — those come from `config.BackendSettings`.

### 4. Interpretability / simplicity scoring
- The family's parameter count is reported in `TransformCandidate.theta`. Flag if unreasonably large.
- The family does not rely on opaque black-box operators disguised as explicit math.

### 5. Reference validation
- Against at least one closed-form target case (e.g., a pure-tone sine input should produce a Lissajous with known ellipse), the implementation matches within documented tolerance.
- Cross-speaker generalization: at least one test runs on a held-out speaker and reports a numeric distance.

## Report

```
=== VALIDATION REPORT ===

Structural completeness : PASS / FAIL (list violations)
Numerical correctness   : PASS / FAIL (list risks)
Data-driven compliance  : PASS / FAIL (list hard-coded literals)
Interpretability check  : PASS / FAIL (parameter count, opacity)
Reference validation    : PASS / FAIL (cite the test case)

Overall: PASS / CHANGES REQUESTED
```