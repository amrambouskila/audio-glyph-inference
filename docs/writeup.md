# Audio-Glyph Operator Inference Writeup

## Status

This writeup is ready for the Phase-5 analysis pass, but the empirical verdict is pending real Stage-7 recordings and user testing. No successful or negative result is claimed here until the 700 planned `.m4a` samples have been uploaded, the feasibility probe has been calibrated, and leave-one-accent-out evaluation has been run.

## Problem

The project asks whether a compact, interpretable operator `F_theta` can map spoken Hebrew-letter audio directly to canonical glyph geometry. The unknown is the transformation itself, not a phoneme label and not a decorative rendering.

For paired examples `(x_i, L_i)`, the fitting objective is:

```text
theta* = argmin_theta sum_i d(F_theta(x_i), L_i) + lambda * Complexity(F_theta)
```

The headline generalization test is accent-disjoint: fit on four accents from the same speaker and evaluate on the held-out accent.

## Data

The planned dataset is one speaker, five accents, 28 spoken audio forms, and five repetitions per `(accent, letter, pronunciation_variant)` block. That yields 700 total raw `.m4a` uploads. The glyph catalog contains 27 written forms: the 22 regular Hebrew letters plus the five sofit forms. The server validates and preprocesses recordings through the documented audio pipeline, then pairs each sample with a STAM-font glyph contour stored in unit-square coordinates.

Current data status:

| Item | Status |
| --- | --- |
| Audio source | User `.m4a` uploads only |
| Speaker count | One project-owner speaker |
| Accent axis | `ashkenazi`, `sephardi`, `moroccan`, `yemenite`, `chabad` |
| Target font | `StamAshkenazCLM.ttf` |
| Real Stage-7 recordings | Pending |

## Methods

The implemented search space is deliberately constrained to avoid a disguised lookup table. The baseline families are Fourier series, Lissajous curves, and phase-space embeddings. The expanded Phase-3 families are audio-driven dynamical systems and symbolic-regression expressions distilled into explicit transform candidates.

The search engine reports:

| Quantity | Meaning |
| --- | --- |
| `mean_shape_distance` | Evaluation split shape-distance data term |
| `simplicity_score` | Reporting score derived from `Complexity(F_theta)` |
| `interpretability_score` | Simplicity multiplied by family prior |
| `lookup_ratio` | Anti-lookup diagnostic comparing within-letter and between-letter generated-contour variance |

Shared-across-letters candidates are the headline candidates. Per-letter candidates are only lookup-ceiling diagnostics.

## Results

Results are pending real recordings. After Stage-7 data exists, this section should be populated from:

- `backend/experiments/*.jsonl` for per-family leaderboards.
- `src.simulation.leave_one_accent_out.evaluate_leave_one_accent_out` for held-out-accent tables.
- `src.simulation.baseline_thresholds.evaluate_exit_gate` for the Phase-2/3 exit-gate verdict.
- `src.simulation.negative_results.render_negative_results_report` for the negative-results transcript.

## Reproducibility

Use the manifest in `backend/experiments/manifests/phase5_pending_real_data.json` as the current reproducibility contract. The notebook `notebooks/phase5_reproducibility.ipynb` loads the manifest and records the table-producing sources without fabricating result data.

Render the deterministic Markdown transcript from the manifest with:

```bash
cd backend
uv run python scripts/render_phase5_report.py --manifest experiments/manifests/phase5_pending_real_data.json --repo-root .. --output ../docs/negative-results.md
```

Expected verification commands before finalizing the empirical writeup:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build
cd ..
docker compose build
```

Frontend live-loop verification remains manual until real saved candidates and glyph targets exist.

## Discussion

The central risk is that audio features encode letter identity well enough for an affine or symbolic map to become a soft lookup table. The project mitigates that risk through structural capacity caps, shared-across-letters preference, leave-one-accent-out evaluation, and the standing `lookup_ratio` diagnostic.

A negative result is valid if the search transcript shows that low-distance candidates either fail held-out accents or collapse to lookup-like behavior. The final conclusion must follow the measured held-out results, not the desired visual outcome.

## Limitations

- Real-data feasibility and exit-gate verdicts are unavailable until Stage-7 recordings exist.
- The live UI requires user-side browser microphone testing to verify the full 27-glyph-form loop and render-rate gate.
- Multi-stroke scoring for detached-stroke letters uses the documented Chamfer substitution unless a future family emits structured multi-stroke contours.

## Conclusion

Pending real-data evaluation.

