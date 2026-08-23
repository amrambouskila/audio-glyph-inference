# Phase 2 â€” Layer 5 (SearchEngine) Design & Session Handoff

> **Purpose:** durable handoff so any new session (Codex or Claude) can implement Layer 5 without re-deriving the design. Read after `AGENTS.md`/`CLAUDE.md`, the master plan, `docs/status.md`, `docs/versions.md`, and `docs/phases/phase-2-plan.md` Â§5.
>
> **State:** Layers 0-6 are implemented + focused-verified to 100% coverage (shape distances, audio features, shared contour primitives, migrated families, scores + exit-gate calibrator, and `SearchEngine`). Layer 6 feasibility-probe core is implemented; Layer 7-8 tracker/ORM/endpoints follow.
>
> **Confidence labels below:** **[VERIFIED]** = produced by a design agent and passed an adversarial-refutation agent (corrections already folded in). **[DRAFT]** = authored in-session, not yet independently verified (a second design+verify workflow `wf_5ffe022c-275` was in flight at handoff; if its results were captured they supersede the drafts and land in Â§5/Â§6).

---

## 0. How to resume

**Post-Layer-6 status:** Layers 0-6 are implemented and focused-verified to 100% coverage. Continue with Layer 7 tracker/ORM/Alembic; the Layer-6 real-data verdict still awaits Stage-7 recordings.

1. Confirm Layers 0â€“4 on disk: `src/simulation/{shape_distance,contour_compare,audio_features,contour_resample,contour_normalize,scoring,baseline_thresholds}.py`, `src/simulation/transforms/{fourier_series,lissajous,phase_space_embedding}.py`, `src/models/exit_gate_result.py`, plus their tests. All currently **uncommitted** (the user manages git).
2. The Â§1 sign-off items were approved by the maintainer (`yes, yes, add field, yes, yes, yes`) and implemented.
3. Continue with Layer 6+ work from `docs/phases/phase-2-plan.md`; keep the Â§0.1 harness pattern for focused 100% verification.

### 0.1 Local verification harness (no venv / no ffmpeg needed)

Run from `backend/`. Scope `--cov` to the modules under test; the coverage config needs `greenlet` and the conftest imports the async DB stack:

```bash
uv run --no-project --python 3.11 \
  --with numpy --with scipy --with pydantic --with pydantic-settings --with pytest --with pytest-cov \
  --with greenlet --with pytest-asyncio --with 'sqlalchemy[asyncio]' --with cma \
  python -m pytest tests/simulation/test_search_engine.py <other test files> \
  -o addopts="" -p no:cacheprovider \
  --cov=src.simulation.search_engine <other --cov=â€¦ modules> \
  --cov-report=term-missing --cov-fail-under=100 -q
```

Full CI (lint → sast → 100%-gated test → build → docker-build) runs on push; the torch-heavy env isn't synced locally.

---

## 1. Maintainer sign-off items (resolved)

| # | Item | Why it needs sign-off | Recommendation |
|---|------|----------------------|----------------|
| 1 | **`FittableFamily` protocol** â€” a new optional `runtime_checkable` Protocol with `fit_theta(...)`, implemented by Fourier + Lissajous, not by phase-space. | Additive (does not modify the frozen `TransformFamily`) but grows the family surface beyond the Stage-1 contract. | Adopt â€” cleanest seam; engine does `isinstance(family, FittableFamily)`, no family-name special-casing. |
| 2 | **Lissajous reparameterization** to the linear form `x = PÂ·sin(at) + QÂ·cos(at)`, `y = RÂ·sin(bt)` (drivers `[P,Q,R]`, equivalent to `A_x=hypot(P,Q), Î´=atan2(Q,P)`). | The current Layer-3 `Î´,A_x,A_y` form is **nonlinear in Î´** and *cannot* be closed-form lstsq-fit; the plan's "Lissajous affine fit by lstsq" (Â§5) only works in the linear form. Reworks `lissajous.py` `forward()` + its Layer-3 tests (mathematically equivalent output). | Adopt â€” required for a closed-form fit; same curve family, just linearly parameterized. |
| 3 | **`TransformCandidate.lookup_ratio: float`** field (the standing anti-lookup `R = Var_within/Var_between` diagnostic). | A Â§3 data-contract change (Pydantic model + ORM row + master plan Â§3.5). | **[DRAFT]** â€” decide: add the field, or keep `R` in the experiment/JSONL side-report. Adding the field is the plan's "standing per-candidate" intent (Â§2). |
| 4 | **New dependency `cma`** (pycma, BSD-3, pure-Python) for CMA-ES. | New runtime dep â†’ `pyproject.toml` + `docs/dependencies.md` + Dockerfile note (no apt change; pure-Python). | Adopt â€” the plan names pycma; do not substitute scipy. |
| 5 | **`fit()` signature annotation refinement** â€” `audio: Sequence[np.ndarray]` (a sequence of per-sample `(num_frames_i, frame_length)` matrices), not `np.ndarray`. | Touches the documented Â§5 fit contract on a stub with no implementation yet. | Adopt â€” `num_frames` varies per sample so a 3D tensor is impossible. |
| 6 | **~10 new `BackendSettings` fields** (Â§8). Three are Â§6 calibration knobs needing eventual sign-off (`search_default_lambda`, `simplicity_c_scale` via existing usage, `search_per_letter_penalty`). | Data-driven config; the calibration values are frozen at Stage-7 kickoff. | Add with Â§6 defaults, flagged as kickoff-calibrated. |

---

## 2. New modules for Layer 5 (one concept per file)

- `src/simulation/batch_features.py` :: `compute_feature_matrix(audio, *, sample_rate_hz, n_mels, n_segments) -> Î¦ (B,D)` â€” the ONLY per-sample loop, run once at fit entry.
- `src/simulation/batch_synthesis.py` :: `synthesize_fourier_batch(phi, theta, num_points)`, `synthesize_lissajous_batch(phi, theta, num_points)`, `_normalize_batch(raw)` â€” `(B,N,2)`, row-normalized, provably equal to `forward()` per row.
- `src/simulation/batch_procrustes.py` :: `procrustes_distance_batch(gen, tgt) -> (B,)`, `chamfer_distance_batch(gen, tgt) -> (B,)`.
- `src/simulation/affine_fit.py` (or as `fit_theta` methods on the families) :: the closed-form ridge fit (Â§5).
- `src/simulation/transforms/family_registry.py` :: `FAMILY_REGISTRY: dict[str, type]`, `build_family(name, settings)`.
- `src/simulation/transforms/fittable_family.py` :: the `FittableFamily` protocol.
- Fill `src/simulation/search_engine.py` :: the `SearchEngine` class.
- `tests/_fixtures/ellipse_family.py` :: `EllipseFamily` test fixture (NOT under `src/`; keep `[tool.coverage.run] source=["src"]` so it isn't coverage-measured, but give it a dedicated test so it's still exercised).

---

## 3. [VERIFIED] Batched scoring (provably equals `forward()`)

**Principle:** keep `forward()` as the single source of truth; the batch path reuses the families' exact primitives (`_basis`/`_synthesize` for Fourier; the sin-stack for Lissajous) over batched arrays, and is locked to `forward()` by an `atol=1e-10` test. The outer loop over *candidates* stays Python; only the within-candidate B-example math is vectorized.

**Feature matrix (sole per-sample loop, at fit entry):** `audio` is a length-B sequence of `(num_frames_i, frame_length)` matrices (`num_frames_i` varies â†’ never a 3D tensor). `Î¦ = np.stack([extract_features(frames_i, sample_rate_hz, n_mels, n_segments) for frames_i in audio])` â†’ `(B, D)`. `D = n_mels + 4 + 4Â·n_segments = 24` at defaults.

**Fourier batched (identical to `forward()` per row):**
```
b = asarray(theta['affine_b'])              # (4K,)   ; K = len(b)//4  (NOT from config)
U = asarray(theta['affine_u']).reshape(4K, r)
V = asarray(theta['affine_v']).reshape(D, r)
VtPhi  = Î¦ @ V                              # (B,D)@(D,r) -> (B,r)
Coeffs = VtPhi @ U.T + b                    # (B,r)@(r,4K)+(4K,) -> (B,4K)   == U@(V.T@Ï†_i)+b per row
cos, sin = _basis(N, K)                     # (N,K) each  (reuse the family primitive)
A,Bc,C,Dc = Coeffs.reshape(B,4,K)[:,0],[:,1],[:,2],[:,3]   # (B,K) each
X = A@cos.T + Bc@sin.T ; Y = C@cos.T + Dc@sin.T            # (B,N) each
Raw = stack([X,Y], axis=2)                  # (B,N,2)
```

**Lissajous batched (after the Â§5 P,Q,R reparam):** `Drivers = Î¦ @ W.T + b0` â†’ `(B,3)`; then the linear synthesis broadcast over `t = 2Ï€Â·arange(N)/N`. (Draft pre-reparam form was `Î´,A_x,A_y` â€” superseded.)

**Per-row normalize (must match `normalize_to_unit_square` row-by-row, NOT a global norm):**
```
Centered = Raw - Raw.mean(axis=1, keepdims=True)            # (B,1,2) per-row centroid over N points
MaxAbs   = abs(Centered).reshape(B,-1).max(axis=1)          # (B,)
Scale    = 0.5 / maximum(MaxAbs, 1e-12)                     # (B,)  same _NORM_EPS floor
return Centered * Scale[:, None, None]
```

**Batched reflection-disabled Procrustes (equals `procrustes_distance` per row):**
```
Ac = Gen - Gen.mean(1, keepdims=True) ; Bc = Tgt - Tgt.mean(1, keepdims=True)    # (B,N,2)
a_norm = sqrt((Ac**2).sum((1,2))) ; b_norm = sqrt((Bc**2).sum((1,2)))           # (B,)
degenerate = (a_norm < 1e-12) | (b_norm < 1e-12)                                 # (B,)
safe_a = where(degenerate, 1.0, a_norm)[:, None, None]   # SHAPE (B,1,1) â€” NOT degenerate[:,None] (that bug broadcasts to (B,B))
safe_b = where(degenerate, 1.0, b_norm)[:, None, None]
An = Ac/safe_a ; Bn = Bc/safe_b
Cov = einsum('bni,bnj->bij', An, Bn)          # (B,2,2) == a.T@b per row (gen LEFT, target RIGHT â€” matches scalar svd(a.T@b))
S   = svd(Cov, compute_uv=False)              # (B,2) descending
BtA = einsum('bni,bnj->bij', Bn, An)          # (B,2,2)
reflection = sign(det(BtA))                   # (B,)
trace = S[:,0] + reflection*S[:,1]
disparity = clip(1.0 - trace*trace, 0.0, 1.0)
out = where(degenerate, 1.0, disparity)       # (B,) _DEGENERATE_PENALTY=1.0, never NaN
```
(Identical contours â†’ `trace = s0+s1 = 1.0` (unit-Frobenius), disparity â†’ 0. NOT `trace=2`.)

**Chamfer batched:** a Python B-loop of two `cKDTree` queries per row, `0.5Â·(mean+mean)/SQRT2` â€” equals `chamfer_distance` per row (KD-trees over independent point sets aren't array-vectorizable).

**Phase-space:** CANNOT use Î¦ (it needs the raw frames, has no affine map). Scored by the literal per-example `forward()` + `contour_compare` loop; the resulting `(B,N,2)` stack still feeds `procrustes_distance_batch`. Tractable (5-scalar search domain).

**Multi-stroke substitution:** rows whose letter âˆˆ `{×”, ×§}` (the real Hebrew glyphs, `constants.HEBREW_LETTERS`; **not** ASCII) are scored with Chamfer regardless of the run's base metric (concatenated multi-stroke target breaks Procrustes correspondence). Per-row, logged once per substituted letter. Config `search_multistroke_metric: Literal["chamfer","error"] = "chamfer"`. Put `MULTI_STROKE_LETTERS: frozenset[str] = {"×”","×§"}` in `constants.py` (font/visual fact, not a tunable).

**THE LOCK TEST (mandatory):** Bâ‰¥6 synthetic samples with **deliberately different `num_frames` each, all â‰¥ `feature_n_segments`** (e.g. `[3,5,8,3,11,4]` â€” NOT 2/1, which yields an empty `array_split` segment â†’ NaN that `assert_allclose(equal_nan=True)` would silently pass). Assert `procrustes_distance_batch(synth_batch(Î¦,Î¸,N), targets) == [contour_compare(family.forward(audio[i],Î¸), targets[i], 'procrustes') for i]` to `atol=1e-10, rtol=0`, **plus** `np.isfinite(...).all()` on both sides so a NaN row fails loudly.

**Wiring:** the engine must build Î¦ with the SAME `sample_rate_hz/n_mels/n_segments` `forward()` reads (capture one `get_settings()` at fit entry; don't let env drift mid-fit).

---

## 4. [VERIFIED] Decode + strategies

**One `_decode(genotype: np.ndarray) -> Theta`** over a normalized `[0,1]^d` vector, `d = len(parameter_space())`, `keys = sorted(parameter_space())` (deterministic layout), `np.clip(genotype,0,1)` guard at entry:
- continuous: `low + gÂ·(high-low)`, EXCEPT keys in `search_log_scale_keys` (default `{'ridge_alpha'}`) â†’ `10**(log10(low)+gÂ·(log10(high)-log10(low)))` (requires `low>0`).
- integer: `int(min(low + floor(gÂ·(high-low+1)), high))`.
- categorical: `choices[int(min(floor(gÂ·L), L-1))]`.

**`_decode` dimensionality caveat (verifier-critical):** the "single shared `_decode`" claim breaks for phase-space CMA if `tau` is pulled into an outer loop while CMA optimizes a 4-vector â€” `_decode` expects `d=5`. **Resolution:** either (a) make the genotype always full length `d` and decode `tau` as a CMA integer coordinate (accept plateaus), or (b) keep `tau` as an outer loop but rename/restructure so `_decode` takes the searched-subset + injected outer keys (drop the "verbatim shared" wording). **Pick one and add a 2-key {continuous, integer} family test so the agree-test isn't blind to `d>1`-with-integer.**

**Strategies:** grid (default; handles integer/small-knob axes â€” Fourier: outer `Kâˆˆ1..fourier_k_max` Ã— `rank_râˆˆ{1,2,3}` Ã— `ridge_alpha` grid; Lissajous: `freq_ratio_a Ã— freq_ratio_b = 25`). CMA-ES reserved for continuous-heavy phase-space. Grid resolution `search_grid_resolution=5` (linspace incl. endpoints; integer axis uses `(arange(M)+0.5)/M` bin centers). Grid count capped at `max_evaluations` via `search_grid_truncation: Literal["error","seeded-shuffle"]="error"` (fail-loud default; shuffle uses `np.random.default_rng(seed).permutation`).

**CMA:** `cma>=3.3.0`; genotype `[0,1]^d`, `x0=full(d,0.5)`, `sigma0=cma_sigma0=0.25`, `options={'bounds':[0,1],'seed':seed,'maxfevals':max_evaluations,'verbose':-9,'tolfun':cma_tolfun}`. **Budget caveat:** do NOT make `tau` a 64-way outer loop on a tight budget (`maxfevals//64` starves CMA to ~random). Cap the tau grid or validate `max_evaluations â‰¥ tau_countÂ·popsize`.

**Constructor validation:** `__init__` validates `strategy âˆˆ {grid, cma-es}` (`bayesian`/`symbolic-regression` â†’ "deferred to Phase 3") and `distance_metric âˆˆ {procrustes, frechet, chamfer}`. `fit()` (NOT `__init__`) validates that `cma-es` â‡’ all *searched* coords continuous (else "cma-es supports only continuous coordinates").

**EllipseFamily recovery test:** fixture `forward = [0.5Â·cos t, bÂ·sin t]`, target `b*` **on the grid lattice** (e.g. `b*=0.275` for R=5 over `[0.05,0.95]`; `0.3` is OFF-lattice â†’ the 3 ellipse tests can't all pass at `atol=2e-2`). Grid recovers `b*` to a grid step; CMA recovers to `atol=1e-2`. **Drop the bitwise-CMA assertion** (BLAS/numpy-version fragile â†’ flakes the 100% gate); instead test determinism on the decoded genotype *sequence* under a fixed seed, and recovery via `assert_allclose(best_b, b*, atol=1e-2)`.

**`_objective` MUST consume precomputed Î¦** (not raw audio + per-call `forward()`), else extract_features is recomputed `BÂ·combos` times (~45Ã— for Fourier).

---

## 5. [DRAFT] Fit-mechanism (pending the in-flight workflow's verification)

**Seam:** `FittableFamily` protocol (Â§1.1). `theta = family.fit_theta(phi, targets, searched_theta, num_points) if isinstance(family, FittableFamily) else dict(searched_theta)`. fit() must branch on this â€” and test BOTH branches (affine family + no-affine family) for 100% coverage.

**Fourier `fit_theta` (linear, exact):**
1. Basis `(2N, 4K)` mapping `[a,b,c,d]` â†’ flattened `(x;y)`. Per example, optimal coeffs reproducing `target_i`: `C_i = lstsq(Basis, target_i.reshape(2N))[0]` â†’ `C (B, 4K)`. (Coeff-space L2 is an accepted **surrogate** for the Procrustes contour objective â€” it ignores the `0.5/max-abs` normalize and Procrustes scale/rotation invariance, but the grid over `rank_r`/`ridge_alpha` + real Procrustes scoring selects the winner.)
2. Ridge with bias: `Î¦_aug = [Î¦, ones] (B, D+1)`; `M_aug = solve(Î¦_aug.T@Î¦_aug + Î±Â·I_{D+1}, Î¦_aug.T@C)` â†’ `(D+1, 4K)`; split linear `M=(D,4K)`, bias `b=(4K,)`.
3. Rank-r factor `M`: `M = PÂ·SÂ·Qáµ€` (SVD); set `V = Q[:, :r]` `(D,r)`, `U = (P[:, :r] * S[:r]).T`? â€” **RESOLVE exactly** so `coeffs = U@(Váµ€Ï†)+b` holds with `U (4K,r)`, `V (D,r)`. (Working form: `M â‰ˆ M_r = (P[:, :r]Â·diag(S[:r])) @ Q[:, :r].T`, where `M` is `(D,4K)` and `coeffs = Máµ€Ï† + b`. So `Máµ€ = Q_rÂ·diag(S_r)Â·P_ráµ€` `(4K,D)`; set `U = Q_r? â€¦` â€” derive carefully; the rank-r identity must be unit-tested.)
4. Pack `affine_u=U.flatten().tolist()`, `affine_v=V.flatten().tolist()`, `affine_b=b.tolist()`; merge with `searched_theta`.

**Lissajous `fit_theta`:** after the Â§1.2 reparam, drivers `[P,Q,R]` are linear in the contour. `C_i = lstsq(LissBasis(a,b), target_i)` â†’ `C (B,3)`; ridge `Î¦_aug â†’ C` â†’ `W (3,D)` + `b0 (3)` (no rank factor â€” 3 drivers ARE the cap). Pack `affine_w`, `affine_b`.

**Layer-3 `lissajous.py` rework (consequence of Â§1.2):** `forward()` becomes `x = PÂ·sin(at)+QÂ·cos(at)`, `y = RÂ·sin(bt)` with drivers `[P,Q,R] = reshape(affine_w,(3,D))@Ï† + affine_b`. Rewrite its tests: ellipse `[P,Q,R]=[0,A_x,A_y]`? (since `Î´=Ï€/2` â‡’ `A_x sin(t+Ï€/2)=A_x cos t` â‡’ `P=0,Q=A_x`); degenerate line `Î´=0` â‡’ `P=A_x,Q=0`; figure-eight `a=1,b=2`; complexity `nnz`. Recompute the closed-form coordinate values in `(P,Q,R)` terms.

**Shared vs per-letter:** shared=True â†’ one `fit_theta` over all B â†’ one candidate. shared=False â†’ 22 per-letter sub-fits â†’ **[OPEN]** represent as 22 `TransformCandidate`s (each `shared_across_letters=False`, `theta`=that letter's packed affine, `mean_shape_distance` over that letter's rows), labeled the lookup-ceiling reference and EXCLUDED from headline/best/gate. Confirm this representation.

**Guards:** `Î±â‰¥1e-4` makes the ridge solvable (no try/except). Guard `num_frames < feature_n_segments` at the fit boundary (NaN from empty `array_split`). Empty slice `B==0` â†’ `ValueError`.

**Reference tests:** (a) known affine map + synthetic `(Ï†, contour)` pairs â†’ recovered coeffs to near-zero error; (b) Fourier `fit_theta` then `forward` reproduces an in-span target to small Procrustes distance; (c) Lissajous `(P,Q,R)` ellipse closed form; (d) rank-r identity `U@(Váµ€Ï†)+b == M_ráµ€Ï† + b`.

---

## 6. [DRAFT] Objective + candidates (pending the in-flight workflow's verification)

**Objective:** `J(Î¸) = mean_data + Î» Â· family.complexity(Î¸) Â· sharing_multiplier`. `mean_data` from the batched scorer (Î¦ for affine families; per-example forward for phase-space; per-row Chamfer for ×”/×§). `mean_shape_distance` stored = `mean_data` only; `J` is the sort key. `Î» = config.search_default_lambda`. `_sharing_multiplier(shared)` = `1.0` if shared else `1.0 + config.search_per_letter_penalty Â· NUM_HEBREW_LETTERS` â€” ONE tested method.

**R diagnostic (anti-lookup, standing per-candidate):** `R = Var_within / Var_between` on Procrustes-residual contours. For each letter: align that letter's generated contours to a reference (same similarity alignment Procrustes uses) and average â†’ letter-mean shape; `Var_within = mean_i ||aligned_i âˆ’ mean(letter_i)||Â²`; `Var_between = Var(letter-means around global mean)`. `Râ†’0` with low distance = lookup. **Storage decision (Â§1.3):** add `TransformCandidate.lookup_ratio` (contract change) vs side-report. **Tests:** a synthetic per-letter-constant ("lookup") candidate â‡’ `Râ‰ˆ0` (FIRES); an audio-varying candidate â‡’ `R` well above 0.

**Determinism seam:** `id: UUID` + `created_at: datetime` are non-deterministic but `fit()` must be seed-reproducible/testable. **[OPEN]** inject a uuid-factory + fixed clock into the engine `__init__`, or have `fit()` return candidates with `id`/`created_at` supplied by the caller. Frozen `fit()` has no such params â†’ decide whether `__init__` takes them; flag any impact.

**Candidate assembly:** `TransformCandidate(id, family=family.name(), theta=packed, shared_across_letters, interpretability_score & simplicity_score via scoring.py with C_scale + per-family prior from config, mean_shape_distance, created_at)`. Sort best-first by `J`; shared-True candidates are the headline/gate set, per-letter are the labeled reference.

**`family_registry.py`:** `FAMILY_REGISTRY: dict[str, type]` + `build_family(name, settings) -> TransformFamily` (stateless except type; read config via `get_settings()`). No hard-coded family strings elsewhere (endpoints/executor use the registry).

---

## 7. Concrete bug-fixes to apply (caught by the adversarial verifiers)

1. Procrustes degenerate guard: `where(degenerate, 1.0, a_norm)[:,None,None]` â€” NOT `degenerate[:,None]` (broadcasts to `(B,B)` â†’ ValueError).
2. Fourier `K = len(affine_b)//4` everywhere â€” there is NO Fourier-K config field.
3. Multi-stroke set = real Hebrew glyphs `{×”, ×§}` â€” NOT ASCII `{'he','qof'}` (else substitution silently no-ops on real data).
4. Lock-test fixtures: all `num_frames â‰¥ feature_n_segments`; assert `isfinite`; `assert_allclose(..., equal_nan=False)`.
5. EllipseFamily target on-lattice (`b*=0.275`, not `0.3`); make all 3 ellipse tests consistent.
6. Drop bitwise-CMA reproducibility; test genotype-sequence determinism + `atol=1e-2` recovery instead.
7. `_objective` consumes precomputed Î¦ (not raw audio + per-call forward).
8. Coincident-contour math: `trace = s0+s1 = 1.0`, not 2.
9. `fit()` branches on `FittableFamily` (don't pack affine onto phase-space/Ellipse).
10. Validation split: strategy/metric in `__init__`; cma-vs-coordinate-kind in `fit()`.
11. EllipseFamily fixture under `tests/_fixtures/` + `[tool.coverage.run] source=["src"]` so it isn't gate-measured, but give it a dedicated test.
12. CMA `tau` outer-loop budget starvation â€” cap tau grid or validate budget.

---

## 8. New `BackendSettings` fields (consolidated)

`search_grid_resolution: int = 5`, `search_grid_truncation: Literal["error","seeded-shuffle"] = "error"`, `search_log_scale_keys: frozenset[str] = frozenset({"ridge_alpha"})`, `fourier_k_max: int = 3`, `cma_sigma0: float = 0.25`, `cma_tolfun: float = 1e-11`, `search_default_lambda: float = 0.01` *(kickoff-calibrated)*, `search_per_letter_penalty: float = 1.0` *(Â§9 Q#3: linear Ã—22)*, `simplicity_c_scale: float = 50.0` *(kickoff)*, `interpretability_prior_fourier: float = 0.8`, `interpretability_prior_lissajous: float = 1.0`, `interpretability_prior_phase_space: float = 0.9`, `search_multistroke_metric: Literal["chamfer","error"] = "chamfer"`. (Mirror as `# BACKEND_*` in `.env.example`; cover in `test_config.py`.) Also `constants.MULTI_STROKE_LETTERS = frozenset({"×”","×§"})`.

---

## 9. New dependency: `cma`

`cma>=3.3.0` (pycma, BSD-3, pure-Python, numpy-only) â†’ `pyproject.toml [project.dependencies]` + `docs/dependencies.md` (rationale vs scipy; license; version-scoped reproducibility) + a Dockerfile comment (no apt change needed).

---

## 10. Build/verify order for Layer 5

0. (sign-off Â§1) â†’ apply the Lissajous reparam to Layer-3 `lissajous.py` + rework its tests; add `cma` dep + config fields + `constants.MULTI_STROKE_LETTERS`.
1. `fittable_family.py` + `family_registry.py` (+ tests).
2. `batch_features.py` â†’ `batch_synthesis.py` â†’ `batch_procrustes.py` (+ the lock test vs `forward()`).
3. `affine_fit.py` / `fit_theta` methods (+ known-map recovery tests).
4. `search_engine.py`: `_decode`, grid/CMA, `_objective` (consuming Î¦), `_sharing_multiplier`, R diagnostic, candidate assembly, constructor validation (+ EllipseFamily recovery, determinism, validation tests).
5. Update `docs/status.md`, `docs/versions.md` (under unreleased `v0.0.2`), this file's status banner.

Each piece to 100% coverage + ruff-clean via the Â§0.1 harness before the next.

---

## 11. Pointers to the in-session design runs (ephemeral)

- Workflow 1 (`w7nprfp7z` / `wf_71453302-f87`): batched-scoring + decode-strategies VERIFIED specs (transcribed into Â§3/Â§4 above). Raw output was at a temp path (may be GC'd).
- Workflow 2 (`wo0kvemji` / `wf_5ffe022c-275`): fit-mechanism + objective-and-candidates â€” in flight at handoff; if captured, its verified results supersede Â§5/Â§6.
