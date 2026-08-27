# Versions

Semver-ordered, newest at top. Version numbers come from `backend/pyproject.toml` â€” never invented or guessed. The release pipeline bumps the source-of-truth field; this document only records what's in each version.

Pre-alpha convention: this project stays on `0.0.x` until the Phase 1 data pipeline actually runs end-to-end. Use **patch** bumps for incremental work during that period. `0.1.0` is reserved for the first version where `POST /api/datasets/audio` + glyph extraction work together on real data.

---

## v0.2.1 — 2026-08-24 (unreleased)

### CI green-up: dependency-audit remediation + three gate fixes (2026-08-27)

The `sast` job was failing on **Backend dependency audit**: `pip-audit` found **42 advisories across 10
packages** in the environment synced from `backend/uv.lock` (last resolved 2026-08-24). Three CI stages were
red or would have gone red; all three are now verified green locally.

**Dependency remediation — `backend/uv.lock`.** Targeted `uv lock --upgrade-package` for exactly the flagged
packages, deliberately *not* a blanket `uv lock --upgrade` (which would also have pulled librosa 1.0.0,
opencv 5.0, redis 8.1, ruff 0.16 and pytest 9.1 into a project gated on 100% coverage of numerical code):

| Package | From | To | Advisories cleared |
|---------|------|----|--------------------|
| `click` | 8.3.2 | 8.5.0 | PYSEC-2026-2132 |
| `idna` | 3.11 | 3.19 | PYSEC-2026-215 |
| `mako` | 1.3.11 | 1.4.1 | PYSEC-2026-2617 |
| `msgpack` | 1.1.2 | 1.2.2 | PYSEC-2026-3625 |
| `pillow` | 12.2.0 | 12.3.0 | 13 advisories (PYSEC-2026-2253..3496) |
| `pydantic-settings` | 2.13.1 | 2.15.0 | GHSA-4xgf-cpjx-pc3j |
| `python-multipart` | 0.0.26 | 0.0.32 | PYSEC-2026-3036/3037/3039/3040 |
| `setuptools` | 81.0.0 | 84.0.0 | PYSEC-2026-3447 |
| `starlette` | 1.0.0 | 1.6.0 | PYSEC-2026-161/248/249/2280/2281 |
| `urllib3` | 2.6.3 | 2.7.0 | PYSEC-2026-141/142 |
| `torch` | 2.12.0 | 2.13.0 | (transitively required — see below) |

`torch` had to move because **torch 2.12 and below cap `setuptools` below 83.0.0**, pinning it onto
PYSEC-2026-3447; `--upgrade-package setuptools` alone was a no-op until torch moved. `torch` and `torchaudio`
are declared but imported nowhere in `src/`, `tests/`, or `scripts/`, so the bump is resolution-only.
`torchaudio` stays at `>=2.2.0`: 2.11.0 is the newest build published on `download.pytorch.org/whl/cpu` and it
declares no `torch` pin. Five direct-dependency floors were raised alongside the lock so that the Dockerfile's
independent `uv pip compile` resolve cannot land on a vulnerable version either.

**CI install correctness — `.github/workflows/ci.yml`.** `uv pip install -e '.[dev]'` was wrong in all three
jobs: `dev` is a PEP 735 dependency-group, not an extra. uv warned `does not have an extra named 'dev'`,
installed 99 packages, and the next `uv run` re-synced them away. Replaced with `uv sync --locked`, which
installs exactly the lock and fails loudly if the lock is stale. **`backend/uv.lock` is now CI-load-bearing:
any `backend/pyproject.toml` edit must be followed by `uv lock`, both committed together.** Verified that
`release.yml`'s `uv version --bump` already keeps the lock in sync, so the release path is unaffected.

**Audit determinism — same file.** The audit only ran at all because `pip-audit` happened to survive
`uv run`'s re-sync. It now audits the exported lock directly:
`uv export --frozen --no-emit-project --no-hashes --all-groups --all-extras --no-emit-package torch
--no-emit-package torchaudio` into `uvx pip-audit --requirement ... --no-deps`. `--all-extras` *widens*
coverage over the previous environment audit (the `symbolic` extra — pysr, sympy, juliacall, juliapkg, semver,
tomlkit — was never installed and so was never audited). The `--no-emit-package` exclusions are mandatory, not
cosmetic: `pip-audit --requirement` runs a pip resolve before auditing anything, and `torch==2.13.0+cpu` exists
only on the PyTorch index, so leaving it in makes the step exit 1 before producing a report. The resulting
audit blind spots are documented in `CLAUDE.md` §13A.

**`docker-build` would have failed next — `backend/Dockerfile`.** Trivy flagged 2 HIGH in the backend image:
`CVE-2026-23949` (jaraco.context 5.3.0) and `CVE-2026-24049` (wheel 0.45.1), both vendored inside the
`python:3.11-slim` base image's system setuptools 79.0.1 under `/usr/local`, where the existing `apt-get
upgrade` layer cannot reach them. Added `RUN python -m pip install --no-cache-dir --upgrade 'setuptools>=84.0.0'`;
setuptools 84 vendors the fixed `jaraco_context` 6.1.0 and `wheel` 0.46.3. Base-image drift, not caused by the
dependency change.

**`docker-build` failed at job setup — `.github/workflows/ci.yml`.** After the above landed, `lint`, `sast`,
`frontend`, `test` and `build` all went green and `docker-build` failed in 3 seconds with
`Unable to resolve action 'aquasecurity/trivy-action@0.28.0', unable to find version '0.28.0'`. Upstream
migrated every tag to a `v` prefix as part of their response to a supply-chain attack (see the
`trivy-action` v0.35.0 release notes) and retained only the unprefixed `0.35.0`; `0.28.0` now 404s while
`v0.28.0` resolves. A pin that worked in June broke with no change on this side. Both Trivy steps are now
`aquasecurity/trivy-action@v0.36.0`, which defaults to Trivy **v0.70.0** (the old pin carried v0.56.1, from
October 2024). The four inputs the workflow passes — `image-ref`, `severity`, `exit-code`, `ignore-unfixed` —
are byte-identical between the two action versions; v0.36.0 only adds `skip-setup-trivy` and
`token-setup-trivy`, both with safe defaults. All 14 action references across both workflow files were
confirmed to resolve.

Worth knowing for the next run: `load: true`, the image `tags:`, and both Trivy steps were all added in
`ae87b90` (2026-08-23) and have **never executed** — the unresolvable action ref killed the job at setup every
time since. The last green `docker-build` (2026-06-23) contains zero Trivy steps and logged
`No output specified with docker-container driver`, confirming `load:` was absent then. So the next run
exercises the second half of that job for the first time. It was de-risked locally with fresh
`--no-cache --pull` builds of both Dockerfiles followed by the exact gate scans.

**`frontend` browser smoke was ~50% flaky — `frontend/playwright.config.ts`.** Measured 3 failures in 6
cold-cache runs, every one `page.goto("/")` exceeding the default 30s per-test timeout while Vite pre-bundled
`three`/`drei`/`chart.js`. Added a top-level `timeout: 180_000`. The worst cold run measured 35.1s locally, and
pinning to 4 logical CPUs (ubuntu-latest's vCPU count) tripled per-test time, which projects ~105s on a cold
runner — 120s was too tight a margin.

**Verified locally, not asserted.** In linux/python3.11 containers matching ubuntu-latest: `uv sync --locked`
succeeds; the audit exits 0 with "No known vulnerabilities found" across 106 packages; three independent
injections of a known-vulnerable pin (`urllib3==2.6.3`, `starlette==1.0.0`, `pillow==12.2.0`) each exit 1 and
name the advisory, proving the gate is not blind; ruff check + format are clean; pytest passes at the 100%
coverage gate against a real Postgres 16; `uv build` produces sdist + wheel; semgrep and gitleaks are clean;
`npm ci`/`npm audit --audit-level=moderate`/lint/vitest (47 tests, 100%)/build all pass; six consecutive
cold-cache Playwright runs pass; and Trivy reports 0 HIGH/CRITICAL on both freshly built images at the
CI-exact `--severity HIGH,CRITICAL --exit-code 1 --ignore-unfixed` settings, using the pinned scanner
**v0.70.0** that `trivy-action@v0.36.0` installs — against a pre-fix baseline image that exits 1 with 2 HIGH.
The pinned scanner and `:latest` (v0.74.0) produce an empty symmetric difference over their finding sets, and
dropping `--ignore-unfixed` surfaces 161 HIGH/CRITICAL, proving the gate is not vacuously green.

**Docs:** `CLAUDE.md` / `AGENTS.md` §5, §12 and §13A (audit command, `uv sync --locked` install, audit blind
spots), `docs/run_guide.md`, `docs/dependencies.md` (new "Version floors and the lock" section),
`docs/status.md`, `.codex/commands/pre-commit.md`. `.gitignore` gains `junit-*.xml` and
`requirements-audit.txt`.

**Semver reasoning:** Patch, folded into the existing unreleased `v0.2.1` (one unreleased version at a time,
per §14). Dependency upgrades, CI configuration, a Dockerfile security layer and a test-timeout change. No
application code, API surface, data contract, host port or test expectation changed.


### Base-image security patch for the alpine runtime stage (2026-08-26)

- **`RUN apk upgrade --no-cache` added to `frontend/Dockerfile`.** The `nginx:1.27-alpine` base currently ships
  `libcrypto3`/`libssl3` 3.5.7-r0, which Trivy flags HIGH (`CVE-2026-14456`, an OpenSSL QUIC-server
  DoS, fixed in 3.5.8-r0). The packages come from the base layer, so nothing in the Dockerfile
  installs them and nothing below can remediate them -- the upgrade has to happen at build time.
  Measured directly against the base image: **2 HIGH before the layer, 0 after**.
- **Why this needed a change at all.** `nginx:alpine` measured clean during the 2026-08-24
  base-image sweep. The advisory landed afterwards. A base image being clean is a point-in-time
  observation, not a property, which is precisely why the patch layer belongs in the Dockerfile
  rather than being skipped on the strength of a past scan. This is the alpine counterpart to the
  `apt-get upgrade` layer the Debian bases already carry.
- **Not gated by CI here.** This repo's pipeline has no `trivy image` step, so the layer is
  preventive hardening rather than a fix for a failing stage. The base-image measurement
  above is what supports it; no image scan is claimed for this repo.

**Semver reasoning:** Patch. A build-time base-image security patch. No application code,
dependency, host port, API or data contract, and no test changed.


### CI hardening + dependency remediation (2026-08-24)

- **Semgrep invocation corrected.** The job used `semgrep ci` with `--severity` and `--error`, which that subcommand does not accept — it exits 2 with a usage error before scanning. Switched to `semgrep scan`, which supports both.
- **Release workflow hardened against script injection.** `${{ inputs.bump }}` and `${{ steps.bump.outputs.new_version }}` were interpolated directly into `run:` blocks, where the value becomes shell code. Both now pass through `env:` and are read as quoted shell variables. The input is `type: choice`, so this was not exploitable today — it is the pattern that breaks the moment the input type changes.
- **Base-image security patches in the Dockerfile.** The Debian slim bases ship a `util-linux` that Trivy flags HIGH (CVE-2026-53612..53615, fixed upstream in 2.41.5). Measured directly: `python:3.13-slim` carries 38 fixable HIGH/CRITICAL, `3.12-slim` 36, `3.11-slim` 38, while `nginx:alpine` is clean. These come from the base layer, so an `apt-get upgrade` step is required even where nothing else installs them.
- **`.trivyignore` added** for two findings with no in-image remediation: `CVE-2025-47273` (setuptools 70.3.0) and `GHSA-6v7p-g79w-8964` (msgpack 1.1.2). Both come from pip's vendored manifest in the base image, not from project dependencies — and setuptools 70.3.0 is not even installed (`find` finds nothing; the image ships 84.x). Upgrading pip does not rewrite that manifest. Each entry carries its justification inline.
- **Dockerfile `missing-user` suppressed with written justification**, per global CLAUDE.md section 9 (non-root is not required for personal local-dev containers). The nginx images additionally cannot run as non-root without the unprivileged image and a port change. Revisit before any deployment beyond localhost.
- **`.semgrepignore` added** for generated artifacts and prose (`PROJECT_DOCUMENTATION.html`, `*.md`, caches). Creating this file replaces semgrep's built-in ignore list, so the standard dependency/build directories and `:include .gitignore` are restated explicitly.
- **`curl | sh` removed from CI.** The four `curl -LsSf https://astral.sh/uv/install.sh | sh` steps in `ci.yml` are replaced with the pinned `astral-sh/setup-uv@v3` action, matching `release.yml` and the rest of the fleet. Semgrep flagged the pipe-to-shell install as a supply-chain risk (`gha-curl-pipe-shell`): a hijacked install script would execute arbitrary code in the runner.
- **Dependency remediation.** `npm audit fix` in `frontend/`; `npm audit --audit-level=moderate` is clean and the frontend build passes.

---

## v0.1.2 - Security documentation + wiring

**Security requirements documented:** `CLAUDE.md` / `AGENTS.md` gain a `<security>` section (§13A) specifying the `sast` CI stage between `lint` and `test` (Semgrep + CodeQL SARIF, ruff `S` family, `eslint-plugin-security` + `eslint-plugin-no-unsanitized`, `pip-audit` / `npm audit --audit-level=high`, gitleaks, Trivy HIGH/CRITICAL on both images), the full input-boundary inventory (audio upload, glyph render, dataset queries, experiments, inference, `/ws/live` MessagePack, stored symbolic expressions via the AST allowlist, frontend/nginx CSP, microphone, CLI scripts, environment, DB rows) with injection classes and required defenses per boundary, and the project-specific additions. The master plan gains a Security section and per-phase SAST gate lines. `.codex/commands/pre-commit.md` gains a SAST audit step and verdict row.

**Sub-docs aligned:** `docs/phases/phase-{1,2,3,4,5}-plan.md` gate lists carry the two new gate lines (SAST green with zero HIGH/CRITICAL and triaged MEDIUM; new input boundaries injection-safe and documented in `<security>`); `docs/phases/phase-2-layer5-design.md` stage list reads lint → sast → test → build → docker-build; `docs/run_guide.md` Tests section lists the local SAST reproduction commands; `docs/status.md` gains a Security section, rewritten into Wired / Still-pending once the wiring landed.

**Security wiring (same version):** `.github/workflows/ci.yml` gains the `sast` job (`needs: lint`, `permissions: security-events: write`) running CodeQL `python,javascript-typescript`, `pipx run semgrep scan --config auto --config p/owasp-top-ten --config p/python --config p/typescript --config p/react --config p/docker --severity ERROR --error --sarif` with SARIF upload plus a fail-on-findings step, `gitleaks/gitleaks-action@v2`, and `uv run pip-audit`; `test` and `frontend` carry `needs: sast`; `docker-build` builds both images with `load: true` and runs `aquasecurity/trivy-action@0.28.0` (`HIGH,CRITICAL`, `exit-code: "1"`, `ignore-unfixed: true`) against each. `backend/pyproject.toml` `[tool.ruff.lint] select` gains `"S"` with `"tests/**" = ["ANN", "S101"]`. `frontend/eslint.config.js` extends `security.configs.recommended` + `noUnsanitized.configs.recommended` (both added as devDependencies), and `frontend/package.json` gains a `sast` script for local parity. `frontend/nginx.conf` gains `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: strict-origin-when-cross-origin`. Pending: a `.semgrep/` rules directory.

---

## v0.0.2 - CI fixes + Stage-1 contract freeze

**All-forms data-contract expansion:** The data contracts now separate base letter, spoken audio form, and written glyph form. `AudioSample` gains `pronunciation_variant` (`plain` / `hard` / `soft`, constrained by base letter), `GlyphTarget` gains `glyph_form` (22 regular + 5 sofit forms), and `PairedExample` denormalizes both fields. The Stage-7 recording plan is now 5 accents × 28 audio forms × 5 repetitions = 700 `.m4a` uploads; sofit forms are rendered glyph targets, not separate recordings. The dataset audit, Phase-5 manifest/report validation, live-smoke seeder, WebSocket smoke pass, frontend catalog contract, recording protocol, and agent-entrypoint summaries are updated accordingly.

**Layer-8 update:** The Phase-2 API endpoints are implemented on the approved-contract fallback path: `POST /api/experiments`, `GET /api/experiments`, `GET /api/experiments/{id}`, and `POST /api/inference` now use the real family registry, `SearchEngine`, JSONL `ExperimentTracker`, Postgres experiment/candidate rows, `AudioPreprocessor`, and shared contour comparison. Because the optional Layer-7 schema additions remain unsigned, run status is derived from `completed_at` and candidate provenance/count is recovered from JSONL. Focused Layer-8 harness: 28 tests at 100% coverage; ruff clean.

**Docker image-hygiene update:** `backend/Dockerfile` no longer installs `build-essential`; all runtime dependencies resolve from wheels under the existing uv/PyTorch-CPU flow. Verified with `docker build -t audio-glyph-inference-backend:local-no-build-essential .` and a container import smoke test for NumPy/SciPy/Numba/OpenCV/SoundFile/Librosa/freetype-py/Torch/Torchaudio/pycma/API/search modules. The local image size is ~695 MB.

**Phase-3 dynamical-system update:** `DynamicalSystemFamily` now implements the Phase-3 audio-driven ODE family with `vanderpol`, `duffing`, and `resonator` modes, categorical/continuous `ParameterSpec`s, Numba RK4 integration, unit-square contour normalization, complexity scoring, and family-registry wiring. Reference tests include a closed-form undamped harmonic oscillator and direct branch coverage for system equations; focused harness: 21 tests at 100% coverage.

**Phase-3 symbolic-expression update:** `SymbolicRegressionFamily` now implements the PySR-output conversion/evaluation layer without importing PySR at runtime: safe scalar coefficient expressions over audio features (`f0..fN`) produce Fourier coefficients, synthesize normalized contours, and report a symbolic complexity proxy. The family registry now constructs `symbolic_regression` for saved-candidate inference, and saved symbolic candidates can be scored without installing the optional `[symbolic]` extra. Focused harness: 34 tests at 100% coverage; transform/search subset: 112 passed; ruff clean.

**Phase-3 PySR proposal/search update:** `symbolic_search.fit_symbolic_regression` now implements the optional `[symbolic]` proposal path: target contours are projected onto the real Fourier basis, PySR fits one scalar expression per coefficient over audio features `f0..fN`, and the expression set is converted into a scored shared `SymbolicRegressionFamily` candidate. `SearchEngine` accepts `symbolic-regression` only for `symbolic_regression`, rejects mislabeled per-letter symbolic searches, and `/api/experiments` preflights the optional PySR extra before creating a run. Focused symbolic/search/API/config harness: 58 tests at 100% coverage; ruff clean.

**Phase-3 Bayesian search update:** `SearchEngine(strategy="bayesian")` now fills the remaining `ExperimentRun.search_strategy` vocabulary path with a deterministic Gaussian-process / expected-improvement optimizer over the existing normalized `ParameterSpec` genotype decoder. The optimizer is dependency-light, uses NumPy plus SciPy's normal CDF, supports mixed continuous/integer/categorical search spaces through `_decode`, and exposes config-driven initial sample count, candidate pool size, RBF length scale, and noise jitter. Focused SearchEngine/config harness: 27 tests passing.

**Bayesian contract reconciliation:** `ExperimentCreate.search_strategy` now reuses the same `SearchStrategy` alias as `ExperimentRun`, so `POST /api/experiments` accepts `bayesian` through the request schema. The Phase-5 manifest and renderer now require the complete `ExperimentRun.search_strategy` vocabulary, including `bayesian`, before a reproducibility transcript can render.

**Bayesian API route coverage:** `tests/api/routers/test_experiments.py` now exercises `POST /api/experiments` with `search_strategy="bayesian"` against real seeded audio/glyph/pair rows. The integration path verifies search execution, persisted run strategy, best-candidate response shape, and strategy-filtered listing without mocking the engine or database.

**Phase-3 leave-one-accent-out harness update:** `leave_one_accent_out.evaluate_leave_one_accent_out` now runs the documented cross-accent evaluation core: for each held-out accent it fits one shared `SearchEngine` candidate on the remaining accents, scores the held-out fold by letter, records per-accent means and best-candidate ids, and optionally attaches the existing exit-gate verdict. New internal model: `LeaveOneAccentOutResult`. Focused harness: 10 tests at 100% coverage; related simulation/model subset: 36 passed; ruff clean.

**Phase-3 leaderboard update:** `leaderboard.build_family_leaderboards` now replays `ExperimentTracker` JSONL ledgers into deterministic per-family rankings using existing `ExperimentRun` and `TransformCandidate` records. The default leaderboard includes only `shared_across_letters=True` candidates for headline reporting, with an explicit option to include non-shared lookup-ceiling references. New internal model: `LeaderboardEntry`. Focused harness: 6 tests at 100% coverage; tracker/leaderboard subset: 9 passed; ruff clean.

**Phase-3 negative-results scaffold update:** `negative_results.render_negative_results_report` now renders deterministic Markdown from per-family leaderboards, leave-one-accent-out results, exit-gate verdicts, and feasibility-probe diagnostics. `docs/negative-results.md` provides the writeup scaffold and explicitly keeps the final verdict pending real Stage-7 recordings. Focused harness: 3 tests at 100% coverage; ruff clean.

**Phase-4 backend live WebSocket update:** `/ws/live` is now implemented and wired into `create_app` as a MessagePack binary WebSocket route. Clients send `configure` frames with candidate/glyph ids, then `audio` frames with 16 kHz PCM16 bytes; the backend returns generated contours, target contours, and shape-distance scores, with protocol errors returned as binary error frames. Focused live/API harness: 8 tests at 100% coverage; ruff clean.

**Live malformed-MessagePack cleanup:** the backend live WebSocket now catches msgpack decode exceptions and returns the existing binary protocol-error frame (`live message must be valid MessagePack`) instead of letting malformed bytes tear down the connection. Focused live-router coverage now sends malformed bytes and then continues using the same socket for additional protocol-error checks; full backend verification remains green at 388 passed, 1 skipped, 100% coverage, with `uv build` passing.

**Live text-frame protocol cleanup:** the backend live WebSocket now validates raw WebSocket events before MessagePack decoding. Text/non-binary frames return the existing binary protocol-error response (`live message must be binary MessagePack`) and the socket remains usable; direct helper coverage also covers malformed event objects and disconnect events. Full backend verification remains green at 389 passed, 1 skipped, 100% coverage, with `uv build` passing.

**Live map-key protocol cleanup:** the backend live WebSocket now rejects MessagePack maps with non-string keys (`live message keys must be strings`) instead of coercing keys to strings. Focused live-router coverage verifies the helper error and continued WebSocket usability after the malformed map-key frame.

**Live configure-UUID protocol cleanup:** malformed `candidate_id` / `glyph_target_id` configure strings now return the same stable binary protocol error as non-string values (`{field} must be a UUID string`) instead of leaking the raw `uuid.UUID` parser message. Focused live-router coverage verifies the helper error and continued WebSocket usability after a malformed configure frame.

**Live outbound-score protocol cleanup:** the backend live WebSocket now validates `score` frames before MessagePack serialization. Non-finite `shape_distance` values and non-finite generated/target contour coordinates are converted into binary error frames instead of being sent to the browser as score payloads. Focused live-router coverage verifies valid score payloads plus non-finite distance and coordinate failures.

**Live finite-score parser hardening:** frontend MessagePack score decoding now rejects non-finite `shape_distance` values and non-finite generated/target contour coordinates before updating Zustand or R3F. Focused utility coverage covers `NaN`/infinite distances and coordinates; refreshed frontend unit verification reports 41 Vitest tests passing at 100% measured coverage.

**Live sample-rate env hardening:** frontend live audio setup now parses `VITE_AUDIO_SAMPLE_RATE_HZ` through a dedicated validator before constructing `AudioContext` or encoding MessagePack audio frames. Missing env still uses the documented 16 kHz live-loop default; malformed, non-positive, or fractional values fail loudly instead of producing `NaN` sample-rate payloads. Focused utility coverage covers default, valid override, and invalid env values; refreshed frontend verification reports 44 Vitest tests passing at 100% measured coverage plus green Playwright browser smoke and build.

**Live outbound-message encoder hardening:** frontend MessagePack encoders now validate configure/audio messages before serialization: candidate and glyph-target ids must be non-empty, scoring metrics must be one of the supported live metrics, audio sample rates must be positive integers, and PCM payloads must be `Uint8Array`s. Focused live-message coverage exercises the invalid runtime cases; refreshed frontend verification reports 45 Vitest tests passing at 100% measured coverage plus green Playwright browser smoke and build.

**Live backend-error cleanup:** frontend live sessions now treat backend `error` frames received after microphone streaming starts as terminal for that configured stream. The UI releases the retained processor/source/media track/audio context, closes the live WebSocket, clears the configured session, and returns to `idle` while leaving the backend error visible for diagnosis. Focused App coverage exercises this post-streaming error path; refreshed frontend verification reports 46 Vitest tests passing at 100% measured coverage plus green Playwright browser smoke and build.

**Shared score-payload validation:** backend live score frames and one-shot inference responses now share `src.api.score_payload.validated_score_payload`, which rejects malformed generated/target contours and non-finite `shape_distance` values before API serialization. `POST /api/inference` validates generated/target geometry before metric evaluation and returns 422 for malformed score geometry. Focused API coverage exercises the shared helper, live route compatibility, and inference rejection path.

**Live configure-target echo:** backend `configured` WebSocket frames now echo `glyph_target_id` with `candidate_id`. The frontend live decoder requires both ids, the connection handshake rejects a mismatched glyph target before entering `CONNECTED`, Playwright mocks use the stricter response shape, and the all-glyph live smoke script verifies the echoed candidate/glyph pair before sending audio. Refreshed verification reports 47 frontend Vitest tests at 100% coverage and 394 backend tests plus 1 skipped host-codec smoke at 100% coverage.

**Phase-4 frontend scaffold update:** `frontend/` now contains the live pronunciation workspace: React 18 + TypeScript strict + Vite, browser microphone capture, raw MessagePack WebSocket frames, Zustand live state, R3F target/generated contour overlay, Chart.js score history, Docker/nginx packaging, compose service wiring, launcher frontend URLs, and CI frontend lint/test/build/docker-build jobs. Frontend utilities are covered by Vitest with the coverage gate; dependency audit is clean.

**Phase-4 live catalog update:** The backend now exposes `GET /api/datasets/glyphs` for listing stored glyph targets with optional letter filtering. The live frontend loads glyph target options from that endpoint and loads candidate options from recent completed experiment details, while preserving manual UUID entry. The WebSocket start path now waits for the socket to open before microphone streaming begins. New frontend catalog parsing tests keep `src/utils/` at 100% coverage.

**Phase-4 score dashboard update:** The live frontend score history now stores the active letter per sample and renders a latest-distance-by-letter summary beside the existing history chart. The Chart.js panes use stable responsive containers so empty datasets do not overlap on desktop or mobile screenshots.

**Phase-4 rate instrumentation update:** The live frontend now computes recent score-update rate from score timestamps and displays it in Hz beside the distance metric, giving the browser UI a direct local readout for the documented >=10 Hz live-loop gate. New utility tests cover rate-window, stale-history, invalid-window, and zero-elapsed edge cases.

**Phase-5 writeup/reproducibility scaffold update:** `docs/writeup.md` now provides the research-note structure for the final report, `backend/experiments/manifests/phase5_pending_real_data.json` records the reproducibility contract for the pending real-data analysis, and `notebooks/phase5_reproducibility.ipynb` is the notebook entrypoint for manifest-backed tables. These artifacts intentionally keep the empirical conclusion pending until Stage-7 recordings and experiment ledgers exist.

**Phase-5 Stage-7 dataset audit:** `backend/scripts/audit_stage7_dataset.py` now checks real Postgres rows against the pending-real-data manifest before searches run. It derives the expected take count from manifest repetitions plus `constants.ACCENTS` / `HEBREW_LETTERS`, reports missing audio takes, extra takes, unpaired audio rows, and missing glyph targets, and supports text or JSON output with a non-zero exit while the dataset gate is incomplete. Focused real-DB harness: 6 tests.

**Stage-7 dataset audit binding hardening:** The Stage-7 audit now verifies that paired examples bind each audio row to a same-letter `PairedExampleRow` and `GlyphTargetRow`. Mismatched audio/pair/glyph letter bindings are reported in text and JSON output and count as unpaired for readiness, so a wrong audio-to-glyph association cannot pass the pre-search gate.

**Phase-5 report command update:** `backend/scripts/render_phase5_report.py` renders the deterministic negative-results Markdown transcript from the Phase-5 manifest, JSONL experiment ledgers, and optional leave-one-accent-out / feasibility-probe result JSON files. Script tests cover real tracker replay, optional result inclusion, stdout/file output, and manifest validation.

**Phase-5 manifest validation hardening:** The report renderer now validates the Phase-5 manifest before reading ledgers: required report fields must be present, the data plan must match `constants.ACCENTS` / `HEBREW_LETTERS` for the 550-sample Stage-7 target, family names must match the transform registry, strategies/metrics must stay within the `ExperimentRun` vocabularies, pipeline and pending-input lists must be non-empty, and target-font/writeup/notebook paths must exist. Focused script tests cover the committed pending-real-data manifest plus invalid total, family, path, font, and required-field failures.

**Phase-5 non-empirical ledger exclusion:** The report manifest now supports `excluded_run_names`, and the pending-real-data manifest excludes `live-smoke-seed` so deterministic browser-smoke ledgers cannot appear in `docs/negative-results.md` as research evidence. The generated report also renders an "Excluded Non-Empirical Runs" section so exclusions are visible rather than silently applied. Focused renderer tests verify that excluded smoke runs are dropped from leaderboards while real ledgers still replay.

**Phase-5 result-artifact validation hardening:** The Phase-5 result models now reject corrupt report inputs before Markdown rendering. `ExitGateResult` validates non-negative counts and pass-count consistency; `FeasibilityProbeResult` validates finite metrics and non-negative distance/ratio values; `LeaveOneAccentOutResult` validates matching accent maps, constants-backed held-out accents, canonical Hebrew letter keys, finite non-negative distances, and exit-gate counts scoped to evaluated accents. The manifest renderer now fails on invalid optional leave-one-accent-out or feasibility-probe JSON instead of producing misleading report text.

**Phase-5 live-loop evidence validation:** `LiveLoopEvidence` now captures the remaining manual browser live-loop gate as an optional manifest artifact. The report renderer includes a Browser Live Loop section and validates that the evidence covers exactly all canonical Hebrew letters, visible score readouts, positive update counts, configured glyph target ids, and score rates meeting the recorded threshold before rendering.

**Phase-5 notebook reproducibility hardening:** `notebooks/phase5_reproducibility.ipynb` now exercises the committed manifest path directly: it imports `render_report_from_manifest`, renders the current transcript, and derives the per-family leaderboard DataFrame from `ExperimentTracker` / `build_family_leaderboards` while applying manifest `excluded_run_names`. A committed-notebook regression test keeps those entrypoints present without inventing empirical rows.

**Phase-5 read-only report rendering:** `ExperimentTracker` now accepts `create=False`, preserving the existing write-capable default for experiment logging while allowing `render_phase5_report.py` to replay ledgers without creating a missing runs directory. Focused tests cover the read-only tracker path and manifest rendering with an absent ledger directory.

**Phase-5 live-loop evidence template:** `backend/scripts/generate_live_loop_evidence_template.py` now emits a complete all-letter browser evidence JSON template for the remaining manual live-loop gate. The generated template is constants-backed and intentionally starts with failing placeholder observations, so it cannot be mistaken for valid report evidence before the user fills real measurements. The CLI now also rejects malformed candidate UUIDs and non-positive score-rate thresholds before writing an evidence file.

**Phase-5 completion audit update:** `docs/completion-audit.md` records the current implemented/prepared/externally-blocked state across Phases 1-5, including the maintainer-owned version/schema/release decisions and the data-dependent gates that must remain open until real recordings and live-loop testing exist.

**Verification-harness update:** Backend audio-upload integration tests no longer require a host ffmpeg binary to pass locally: they generate a soundfile-decodable synthetic upload payload while still exercising the real dataset router, canonical `.m4a` storage path, `AudioPreprocessor.load`, validation cleanup, persistence, and duplicate-take handling. The committed `.m4a` fixture remains covered by a conditional decode smoke test when ffmpeg/audioread is available. Verified with `uv run pytest` at 100% backend coverage.

**Verifier-noise cleanup:** Removed stale `ANN101`/`ANN102` ruff ignores that no longer exist in current ruff, and switched API routers from deprecated FastAPI status aliases to `HTTP_422_UNPROCESSABLE_CONTENT` / `HTTP_413_CONTENT_TOO_LARGE` while preserving response status values. Verified with affected API tests, full backend pytest at 100% coverage, ruff, and `uv build`.

**Runtime compose verification:** `docker compose up -d` now starts Postgres, Redis, backend, and frontend on the documented ports. Host checks passed for backend `/health`, frontend `/`, and `GET /api/datasets/glyphs?limit=1` on a fresh DB; the frontend healthcheck now probes `127.0.0.1` instead of `localhost` to avoid an in-container localhost resolution mismatch.

**Launcher verification hardening:** `run_audio_glyph_inference.sh` is normalized to LF so Bash can execute it on Windows-hosted checkouts, with `.gitattributes` preserving `.sh` LF and `.bat` CRLF on future checkouts. Both launchers now detach startup/teardown subprocesses from menu stdin. The shell launcher also tolerates CRLF piped input, and the batch launcher exits cleanly on menu EOF plus supports `AGI_AUTO_CHOICES` for deterministic scripted menu verification. This preserves the `[k]/[q]/[v]/[r]` control paths while keeping normal interactive behavior unchanged.

**Verification refresh:** After the launcher changes, the full backend verification matrix was rerun (`ruff check`, `ruff format --check`, `pytest`, `uv build`) and the frontend lint/test/build matrix was rerun with the Windows-safe `npm.cmd` entrypoint. The run guide now notes the `npm.cmd` PowerShell workaround for hosts where `npm.ps1` is blocked by execution policy.

**Source hygiene pass:** `FittableFamily.fit_theta` now uses the same protocol no-op body style as `TransformFamily` instead of raising `NotImplementedError`, and its protocol test covers the super-call path. Implemented backend/frontend source was scanned for TODO-style markers, `NotImplementedError`, and debug `print()` calls with no remaining source hits.

**Master-plan sidecar reconciliation:** Master plan §11.1 now matches the previously approved reconstruct-not-store ingestion decision: `POST /api/datasets/audio` persists only the raw `.m4a`; preprocessed audio is regenerated on demand, with no `.wav` sidecar and no `wav_path` field.

**Agent-entrypoint contract reconciliation:** `AGENTS.md` and `CLAUDE.md` §8 now list the current frozen contract fields for `AudioSample`, `TransformCandidate`, and `ExperimentRun`, including `repetition`, `expression`, and the run reproducibility fields already present in the master plan and Pydantic models.

**Frontend API-contract hardening:** `frontend/src/types/apiModels.ts` now mirrors the backend Pydantic contracts for `AudioSample`, `GlyphTarget`, `PairedExample`, `TransformCandidate`, `ExperimentRun`, and experiment details. The live catalog types now derive their summaries from those full API models, keeping the Phase-4 TypeScript contract aligned with the frozen data shapes.

**Frontend catalog parser hardening:** The live catalog parser now rejects array-shaped payloads when object-shaped glyph targets, experiment runs, or experiment details are required. Focused tests cover these malformed API shapes so stale or malformed catalog responses fail at the correct contract boundary.

**Generated-artifact ignore hardening:** `.gitignore` now ignores generic `coverage/` directories so frontend Vitest coverage output is not accidentally committed when `frontend/` is added.

**Runtime-artifact ignore hardening:** `.gitignore` now ignores generated experiment JSONL ledgers at `backend/experiments/*.jsonl` and nested contour `.npy`/`.npz` files under `backend/data/contours/**`. The Phase-5 manifest directory remains visible, so reproducibility contracts can still be reviewed while smoke/runtime outputs stay out of `git status`.

**Phase-4 live smoke-data seeder:** `backend/scripts/seed_live_smoke.py` seeds a fresh database with catalog-visible glyph targets for all 22 letters plus one deterministic completed `lissajous` smoke run/candidate, allowing browser live-loop round-trip testing before real experiment candidates exist. The seeded candidate is explicitly non-empirical and does not satisfy Phase-2/3 exit gates. `src.config_snapshot.config_snapshot` now centralizes ExperimentRun config-snapshot flattening for both the API endpoint and script. `backend/Dockerfile` now copies `scripts/` into the image and sets `PYTHONPATH=/app` so the documented Docker exec command can import `src`. Full backend verification now reports 379 passed, 1 skipped, 100% coverage.

**Phase-4 live catalog auto-select:** The frontend now auto-selects the first fetched candidate and glyph target when the fields are empty, also setting the active letter from the selected glyph. Manual UUID entry remains available. A new React component test covers the seeded-catalog path; refreshed frontend verification reports 19 Vitest tests passing, utility coverage 100%, lint clean, build clean, and a rebuilt frontend Docker image serving HTTP 200.

**Phase-4 live configure-handshake hardening:** The frontend live-loop connection now resolves only after the backend sends a `configured` response for the selected candidate, and an already-open socket is reused only when it matches the current candidate/glyph selection. Backend configure errors now stop microphone startup before `getUserMedia` is requested. Focused React component tests cover delayed connected status and configure-error rejection; refreshed frontend verification reports 21 Vitest tests passing, utility coverage 100%, lint clean, and build clean.

**Live failed-configure socket cleanup:** configure-time backend errors and malformed pre-configuration responses now close and clear the failed live WebSocket immediately after rejecting the handshake. The existing configure-error component test now asserts that microphone access is not requested and the failed socket reaches `CLOSED`, preventing rejected configure attempts from lingering until the next user action.

**Phase-4 all-glyph live smoke command:** `backend/scripts/smoke_live_roundtrip.py` now gives the seeded catalog a deterministic backend preflight: it selects the latest completed run's best candidate, discovers the configured font/raster glyph targets for all 22 Hebrew letters, configures `/ws/live` once per glyph, sends a synthetic PCM16 frame, and fails on any missing score response. The run guide documents the command after `seed_live_smoke.py`. Focused script tests cover target discovery, latest-candidate selection, payload validation, and CLI output. Runtime Docker verification passed for all 22 seeded glyph targets.

**Live short-window feature robustness:** `audio_features.extract_features` now keeps per-segment descriptors finite when a live audio window contains fewer frames than `feature_n_segments`, reusing the nearest available frame for empty short-window segments. The live WebSocket route now returns a MessagePack error frame for scoring `ValueError`s instead of dropping the connection. Tests cover finite short-window features and scoring-error protocol behavior.

**Live frontend status-state hardening:** the Zustand live store now clears transient errors without forcing the session status back to `idle`, so catalog refreshes or recovered errors cannot make an active connected/streaming socket look disconnected. Store-level Vitest coverage verifies clear-error preservation, error state transition, and score acceptance; refreshed frontend verification reports 24 tests passing at 100% utility coverage.

**Live R3F overlay coverage:** `LiveCanvas` now has deterministic jsdom component coverage with mocked R3F/drei primitives. The tests verify the orthographic camera/control configuration, target/generated line colors and widths, z-layer separation for overlays, and suppression of singleton contours. Refreshed frontend verification reports 26 tests passing at 100% utility coverage.

**Live score-dashboard coverage:** `ScoreChart` now has deterministic component coverage for the Chart.js dashboard boundary. The tests verify score-history line datasets, latest-distance-by-letter bar datasets, stable empty-history datasets, and the non-animated responsive chart options used by the live UI. Refreshed frontend verification reports 30 Vitest tests passing at 100% measured frontend coverage.

**Live browser canvas/rate smoke:** The frontend now has a Playwright Chromium smoke test for the real R3F canvas across desktop and mobile viewports. The test mocks only catalog/WebSocket browser boundaries, feeds multiple MessagePack score frames, verifies the live status/score plus visible `10.0 Hz` rate readout, and decodes a canvas screenshot with `pngjs` to assert nonblank generated and target pixels. CI installs Chromium and runs `npm run test:browser` before the frontend build.

**Live microphone lifecycle coverage:** the frontend successful microphone path now has component coverage with a mocked browser audio graph. The tests verify `getUserMedia`, `AudioContext({ sampleRate: 16000 })`, MessagePack `audio` frames containing PCM16 bytes, stop-path cleanup, and unmount cleanup. `App` now retains the media source node and disconnects it on stop/component teardown alongside the processor, tracks, audio context, and WebSocket. Refreshed frontend verification reports 28 tests passing at 100% utility coverage.

**Live microphone duplicate-start guard:** the frontend now ignores repeated Start microphone clicks while microphone startup is already in flight, preventing duplicate sockets, media streams, or audio contexts during manual live-loop testing. A focused component test covers the rapid-click path, and refreshed frontend verification reports 31 Vitest tests passing at 100% measured frontend coverage.

**Live configured-letter scoring:** the frontend now binds score-history samples to the configured glyph target's catalog letter instead of the mutable free-text Letter field, preventing the per-letter score dashboard from being mislabeled if the field changes after connection. A focused component test covers the drift case, and refreshed frontend verification reports 32 Vitest tests passing at 100% measured frontend coverage.

**Live duplicate-connect guard:** the frontend now reuses the in-flight configure handshake when Connect is clicked repeatedly for the same candidate/glyph pair, preventing duplicate WebSockets before the backend responds. A focused component test covers the rapid-click path, and refreshed frontend verification reports 33 Vitest tests passing at 100% measured frontend coverage.

**Live audio-graph failure cleanup:** the frontend now cleans up after browser audio graph setup failures that occur after microphone permission is granted: the just-opened media stream is stopped, the startup guard is cleared, the error is surfaced, and a later Start microphone retry can reuse the configured socket. A focused component test covers the failure-and-retry path, and refreshed frontend verification reports 34 Vitest tests passing at 100% measured frontend coverage.

**Live socket-drop cleanup:** the frontend now releases microphone resources when the live WebSocket unexpectedly closes or errors during streaming. The socket handlers clear configured-session state, tear down the audio graph, stop media tracks, and surface the socket closure/error instead of leaving the browser microphone active without score updates. A focused component test covers unexpected close during streaming, and refreshed frontend verification reports 35 Vitest tests passing at 100% measured frontend coverage.

**Live streaming reconfiguration cleanup:** the frontend now releases the active microphone/audio graph before replacing a streaming session's WebSocket when the user changes candidate/glyph selection and presses Connect. The replacement socket starts from an idle configure handshake, preserving the duplicate-start guard while preventing stale microphone capture from feeding a new session. A focused component test covers streaming reconfiguration, and refreshed frontend verification reports 36 Vitest tests passing at 100% measured frontend coverage.

**Live socket-error close cleanup:** the frontend now actively closes an errored live WebSocket after clearing the active socket ref, preventing the close handler from double-reporting while ensuring the browser/socket object does not remain open after an error. A focused component test covers streaming socket-error cleanup, including audio graph teardown, media-track stop, context close, and socket `CLOSED` state; refreshed frontend verification reports 37 Vitest tests passing at 100% measured frontend coverage.

**Live malformed-response cleanup:** the frontend now treats undecodable post-configuration binary WebSocket responses as protocol failures: it releases microphone resources, closes the live socket, clears the configured session, returns the UI to `idle`, and surfaces the decoder error. A focused component test covers malformed bytes during streaming; refreshed frontend verification reports 38 Vitest tests passing at 100% measured frontend coverage.

**Live socket-constructor failure guard:** the frontend now handles failures while constructing the browser WebSocket object itself. Connect shows the constructor error instead of swallowing it, and Start microphone aborts before requesting microphone access if the socket cannot be created. Focused component tests cover both paths; refreshed frontend verification reports 40 Vitest tests passing at 100% measured frontend coverage.

**Layer-7 update:** The approved-contract tracker/ORM/Alembic path is implemented: `ExperimentTracker` writes and replays one JSONL ledger per run, `ExperimentRunRow` and `TransformCandidateRow` mirror the current Pydantic contracts field-for-field using JSONB for `config_snapshot`/`theta`, Pydantic models support ORM `from_attributes`, and `0002_experiment_tables.py` creates/drops the experiment tables. Focused Layer-7 harness: 26 tests at 100% coverage; ruff clean. The optional `status` column and candidate provenance FK remain pending maintainer sign-off.

**Layer-6 update:** The feasibility-probe core is implemented: pure affine-Fourier ridge fit, held-in/held-out Procrustes metrics, per-letter/global constant baselines, shared `lookup_ratio` diagnostic, `FEASIBLE` / `TRIVIAL_LOOKUP` / `NO_FIT` classifier, internal `FeasibilityProbeResult`, and an NPZ-to-JSON CLI driver. Focused Layer-6/SearchEngine diagnostic harness: 41 tests at 100% coverage; ruff clean. The real verdict remains gated on Stage-7 recordings and calibrated `rho_min`.

### Fixed

- `uv build` in GitHub Actions failed on the wheel-from-sdist step because `backend/pyproject.toml`'s `readme = "../README.md"` reached outside the package root; parent-relative paths cannot travel inside an sdist, so hatchling's metadata validation aborted the wheel build. Replaced with a dedicated `backend/README.md` and set `readme = "README.md"`. Root `README.md` remains the project-wide doc; the new file is backend-package-scoped.
- `docker-build` job failed on `backend/Dockerfile` line 41 with `Syntax error: "(" unexpected`. The dependency-install `RUN` layer used bash process substitution (`<(uv pip compile pyproject.toml)`), which `/bin/sh` (dash, the default `RUN` shell on `python:3.11-slim`) does not support. Replaced with a two-step `uv pip compile -o /tmp/requirements.txt` + `uv pip install -r /tmp/requirements.txt` (POSIX-sh compatible, same intent, cacheable).

### Changed â€” data contracts (Stage-1 freeze; pre-alpha patch per CLAUDE.md Â§14)

Contract *shapes* frozen before Phase 2 builds on them; all bodies still raise `NotImplementedError`.

- **`AudioSample`** gains first-class `repetition: int` (>0); uniqueness is `(speaker_id, accent, letter, repetition)`. Master plan Â§3.2 updated; the ORM column + `UniqueConstraint` land in Stage 3.
- **`TransformCandidate.theta`** widened from `dict[str, float]` to `dict[str, float | int | list[float] | str]` (Fourier order K, coefficient lists, categorical/symbolic tags) and gains `expression: str | None` for symbolic candidates (stored JSONB in Stage 2). Master plan Â§3.5 updated.
- **`ExperimentRun`** gains the Â§2/Â§10 objective + reproducibility fields: `regularization_weight` (Î»), `rng_seed`, `font_name`, `config_snapshot`, `held_out_accent`. `search_strategy`/`scoring_metric` tightened to `Literal` vocabularies. Master plan Â§3.6 updated.
- **`PairedExample.split`** tightened to `Literal["train", "val", "test"]`; semantics corrected to accent-disjoint (was "per speaker"). Membership validators added to `letter`/`accent` on AudioSample, GlyphTarget, PairedExample.
- **`TransformFamily` protocol** (`transform_base.py`): `parameter_space()` now returns `dict[str, ParameterSpec]` (continuous / integer / categorical) instead of float-box tuples; added `complexity(theta) -> float` for the Â§2 objective; `forward()`/theta typed via the widened `Theta` alias. `transform-protocol` skill updated to match.
- **`SearchEngine.fit`** redesigned from label-blind `(audio_batch, target_batch)` to carry `letters`, `accents`, `shared_across_letters`, and `seed`, returning `list[TransformCandidate]`; `__init__` gains `regularization_weight` (Î»).
- **`shape_distance`** functions documented with the lower-is-better / `0.0`==identical / unit-normalized return contract; FrÃ©chet start-point/winding requirement noted.

### Added

- `src/simulation/transforms/parameter_spec.py` â€” `ParameterSpec` (continuous / integer / categorical search-domain declaration with cross-field validation) plus full-branch test coverage in `tests/simulation/transforms/test_parameter_spec.py`.
- `.env.example` (committed dev defaults: `POSTGRES_*` / `REDIS_PORT` / `BACKEND_*` + commented Phase-4 `VITE_*`) and a `!.env.example` negation in `.gitignore`.

### Changed â€” docs (Stage-0 reconciliation)

Repo-wide drift sweep so the mandatory session-start re-read is accurate:

- **GitLab â†’ GitHub Actions** (`.github/workflows/ci.yml` + `release.yml`) across CLAUDE.md/AGENTS.md/README/master-plan Â§9/phase-1-plan; the Â§5 CI sections rewritten to the real jobs.
- **`.claude/` â†’ `.codex/`** (hooks + commands) **+ `.agents/skills/`** in both agent files' Â§11 trees, with a harness-sync note; `.codex/settings.json` references corrected to `.codex/hooks.json`.
- **`WAV/FLAC` upload â†’ `.m4a`** (endpoint inventory + Phase-1 gates + master plan Â§9).
- **Speaker axis â†’ accent axis:** cross-speaker / speaker-disjoint / â‰¥2-speakers rewritten to accent-disjoint / leave-one-accent-out (master plan Â§1/Â§6/Â§9, phase-2/3/5 plans, validation-protocol + phase-awareness skills, `/validate`).
- **Dropped the resolved-away "public-dataset ingester"** (master plan Â§6, Â§7 FORVO node â†’ `.m4a` upload, Â§10 open-question â†’ resolved; phase-1-plan); `httpx` re-justified as the async test client.
- Font documented as **committed**; Â§15 empty-state corrected to `AttributeError` (unassigned module-level `app`) not `NotImplementedError`; `constants.py` accent comment corrected to four-in/one-out-of-five; `.codex/hooks.json` macOS memory path genericized; `phase-1-plan` task numbering de-duplicated.

### Changed â€” config & infra (Stage 2)

- `config.BackendSettings` gains the audio-ingest validation/normalization fields so recording-protocol Â§3/Â§7 thresholds are data-driven, not hard-coded into the (future) preprocessor/router: `audio_duration_min_s`/`max_s`, `audio_active_speech_min_s`/`max_s`, `audio_silence_pad_max_s`, `audio_peak_dbfs_max`, `audio_target_lufs`, `audio_default_speaker_id`, `audio_max_upload_bytes`. Mirrored as overridable `# BACKEND_AUDIO_*` entries in `.env.example`; covered in `test_config.py`.
- `constants.ACCEPTED_AUDIO_MIME_TYPES` â€” allowlist for the `.m4a` upload endpoint (Â§7); covered in `test_constants.py`.
- Launchers: `.bat` now respects `BACKEND_PORT`/`POSTGRES_PORT`/`REDIS_PORT` env overrides (was hard-coded `8000`/`5432`/`6379`); the `[r]` restart no longer force-removes images every cycle in either script (it was conflated with `[q]`); `.sh` `set -e` no longer aborts before the menu on a slow/failed boot (`start_service || true`); `[k]` teardown gains `--remove-orphans` for symmetry.
- CI (`ci.yml`): the `test` job gains a `postgres:16-alpine` service + `BACKEND_DATABASE_URL` (pre-positioned for the Stage-3 real-DB integration tests); the 100% gate is now explicit at the call site (`--cov-fail-under=100`); `docker-build` also runs on pull requests (catches Dockerfile drift in review). `release.yml` aligned to Python 3.11.

### Changed â€” data layer (Stage 3)

- The 3 Phase-1 ORM rows (`audio_sample_row`, `glyph_target_row`, `paired_example_row`) now carry real columns mirroring their Pydantic models, incl. `repetition`, the `(speaker_id, accent, letter, repetition)` `UniqueConstraint`, and the paired-example foreign keys. The 3 Phase-1 Pydantic models gain `model_config = ConfigDict(from_attributes=True)` for the `model_validate(row)` boundary. (transform_candidates / experiment_runs stay Phase-2 stubs.)
- `data/database.py` implements `create_engine`, `create_session_factory`, and an `@asynccontextmanager session_scope` (commit-on-success / rollback-on-error). `data/orm/__init__.py` re-exports all rows so `Base.metadata` is populated for Alembic + `create_all`.
- Alembic scaffolded: `alembic.ini`, async `migrations/env.py` (URL from `BackendSettings`, metadata from `Base`), and `migrations/versions/0001_baseline.py` creating the 3 Phase-1 tables. `backend/entrypoint.sh` runs `alembic upgrade head` then `exec uvicorn`; the Dockerfile copies the alembic assets + entrypoint and sets it as `ENTRYPOINT`.
- Tests: `conftest.py` provides a real-Postgres fixture â€” `testcontainers` locally (zero setup beyond Docker), CI's `services: postgres` via `BACKEND_DATABASE_URL`. Round-trip + unique-constraint + FK tests for the 3 rows; `session_scope` commit/rollback tests. `testcontainers[postgres]` added to the dev group; the `migrations/**` ruff E402 ignore added for the env bootstrap.
- **Verified against real Postgres:** 48 data/model tests pass, `src/data` 100% covered, `alembic upgrade head` creates exactly `audio_samples` / `glyph_targets` / `paired_examples`, ruff clean.

### Changed â€” glyph extraction (Stage 4; data-contract: +num_contours, pre-alpha patch)

Decision #5 resolved: an empirical 22-letter sweep showed 20 letters are single-stroke; ×” (U+05D4) and ×§ (U+05E7) have a detached stroke that "largest contour" would drop (~18% / ~29% of the ink). Maintainer chose **ordered multi-contour** (Option C).

- `GlyphExtractor.extract` implemented â€” freetype render (glyph centered, clip-safe) â†’ OpenCV `RETR_EXTERNAL` (all strokes, ordered largest-first) â†’ per-contour arc-length resample with points allocated by perimeter share of `glyph_contour_num_points` â†’ joint centroid-centering + y-up flip + joint scale into `[-0.5, 0.5]`. Returns an ordered `list[(n_i, 2)]` (1 entry for most letters; 2 for ×” / ×§).
- **Data-contract change (Â§3.3):** `GlyphTarget` gains `num_contours`; `contour_path` is now an `.npz` of ordered stroke contours; `num_points` is the total across strokes. Propagated to the Pydantic model, the ORM row, the `0001_baseline` migration (`glyph_targets.num_contours`), master plan Â§3.3/Â§9.4, and CLAUDE.md/AGENTS.md Â§8.3/Â§9.4.
- **Verified against the real font + real Postgres:** all 22 letters produce valid in-range contours (×”/×§ â†’ 2), `glyph_extractor` at 100% coverage (53 tests), the `num_contours` column round-trips, `alembic upgrade head` creates it, ruff clean.

### Added â€” audio pipeline + FastAPI API (Stages 5â€“6)

- **`AudioPreprocessor`** (`decode` / `preprocess` / `load`): m4a/wav decode â†’ validate duration + peak dBFS â†’ 16 kHz resample â†’ âˆ’23 LUFS (pyloudnorm) â†’ VAD-trim (librosa) â†’ validate active-speech â†’ frame, clipped to `[-1, 1]`. Returns `PreprocessResult` (frames + native rate + post-trim duration + peak dBFS); rejections raise `AudioValidationError`. New config knob `audio_vad_top_db`.
- **FastAPI app** â€” `create_app` + a module-level `app = create_app()` (lifespan-managed engine; the container now starts), with per-request DB-session + config-built-engine/preprocessor/extractor dependencies. `/health` returns 200.
- **`/api/datasets/*`** â€” `POST /audio` (multipart `.m4a` + form fields; MIME/size/path-traversal guards; store â†’ preprocess/validate â†’ insert `AudioSample`; 409 on duplicate take), `POST /glyphs` (render â†’ save `.npz` â†’ insert `GlyphTarget`), `POST /pairs` (associate; 404/422 guards), `GET /pairs` (filter by split/letter/accent + pagination).
- **`contour_io`** (save/load the ordered contour `.npz`) and the **`PairedExampleCreate`** request model.
- **Tests:** real-Postgres integration tests (httpx + testcontainers) for every endpoint and branch; the committed `.m4a` fixture (`backend/tests/fixtures/test-sample.m4a`); `AudioPreprocessor` DSP/validation unit tests; `contour_io` round-trip. `[tool.coverage.run]` gains `concurrency = ["thread", "greenlet"]` so SQLAlchemy-async post-await lines are traced.
- **Verified locally:** the full backend suite is **152 passed at 100% coverage** (`--cov-fail-under=100`), ruff clean; the real `.m4a`â†’ffmpeg decode runs in CI / the backend image (locally via an ffmpeg shim).

### Decision resolved

- **#10 (derived WAV):** not persisted â€” the `.m4a` is the source of truth and the preprocessed signal is regenerable on demand; no `.wav` sidecar and no `wav_path` field (contract unchanged). `docs/recording_protocol.md Â§5â€“Â§7` updated to drop the WAV-write step.

### Changed â€” Docker image: CPU-only torch pin (audit #20)

- `pyproject.toml` routes `torch`/`torchaudio` through the PyTorch CPU wheel index (`[[tool.uv.index]]` + `[tool.uv.sources]`) with `index-strategy = "unsafe-best-match"` â€” both PyPI and the official PyTorch index are trusted, and the strategy is needed because the PyTorch index mirrors common deps (e.g. `certifi`) that would otherwise shadow the newer PyPI versions under uv's default first-index-wins resolve. The Dockerfile install step adds the matching `--extra-index-url` so the pinned `+cpu` wheels are locatable in the flat requirements file.
- **Verified end-to-end:** `docker build` succeeds; `torch==2.12.0+cpu` / `torchaudio==2.11.0+cpu` resolve; image â‰ˆ **3.4 GB** (vs the multi-GB-larger CUDA build the default index pulls).

### Added â€” Phase 2 search internals (buildable-now layers; closed-form-verified)

Per `docs/phases/phase-2-plan.md`. Each layer is unit-tested to 100% before the next builds on it; every test is closed-form / reference (no tautologies). Layers 0-8 are now implemented on the approved-contract fallback path; the feasibility-probe verdict and exit gate still await Stage-7 real data.

- **Shape distances (Layer 1):** `shape_distance.py` â€” `procrustes_distance` (full-Procrustes after similarity alignment, **reflection disabled** since Hebrew letters are chiral), symmetric `chamfer_distance` (cKDTree), discrete `frechet_distance` (cyclic-shift + reversal start-point resolution); Chamfer/FrÃ©chet are `âˆš2`-normalized via new `constants.SQRT2`. `contour_compare.py` dispatches the three by metric name (the single helper the engine and `/api/inference` share). 24 tests.
- **Audio features (Layer 2):** `audio_features.extract_features` â†’ Ï† âˆˆ â„Â²â´ = [log-mel means | global spectral descriptors | per-time-third descriptors], pure NumPy, deliberately transient-retaining (anti-lookup design Â§2). New config `feature_n_mels` (8) / `feature_n_segments` (3). 10 tests.
- **Shared contour primitives (Layer 0):** lifted `GlyphExtractor._resample_closed` â†’ `contour_resample.resample_closed` (re-imported by the extractor; no behavior change) and extracted `contour_normalize.normalize_to_unit_square` (centroid-center + 0.5/max-abs, eps-floored) shared by the affine families.
- **Transform families (Layer 3):** the three Phase-2 stubs migrated to the Stage-1 protocol (`parameter_space() -> dict[str, ParameterSpec]`, `complexity(theta) -> float`, `forward(audio, theta) -> (N, 2) float64 in [-0.5, 0.5]`) with real, pure, deterministic implementations:
  - **Fourier** (`fourier_series`): real-linear closed trig polynomial; its 4K coefficients come from a rank-r affine map of Ï† (`coeffs = UÂ·(Váµ€Ï†) + b`). Searched Î¸: `rank_r` (1â€“3), `ridge_alpha`. Fitted Î¸ (closed-form lstsq in Layer 5): `affine_u`/`affine_v`/`affine_b` (list[float]); K read back from `len(affine_b)//4`. Tests: exact orientation-pinned ellipse, exact synthesis linearity, fills-box containment, varies-with-audio (anti-collapse), nonzero signed area, MDL complexity.
  - **Lissajous** (`lissajous`): coupled sinusoids with integer ratios (`freq_ratio_a`/`freq_ratio_b`, searched) and 3 continuous drivers (Î´, A_x, A_y) from a small affine of Ï†; the ratios are global (cannot encode 22 letters). Tests: ellipse axis-ratio, degenerate line, figure-eight self-intersection, ratios-are-global, complexity.
  - **Phase-space** (`phase_space_embedding`): overlap-reconstruct the 1D signal â†’ standardize â†’ Takens delay embed (Ï„) â†’ rigid placement (gain/rotation/center) â†’ arc-length resample â†’ clip. No learned audioâ†’param map, so it structurally cannot memorize. Tests: Ï‰Ï„=Ï€/3 covariance-eigenvalue ratio = tanÂ²(Ï€/6), rigid gain/rotation/center closed forms, degenerate all-zero collapse, complexity.
- New config `complexity_bits_per_param` / `complexity_order_penalty` / `complexity_struct_cost` â€” MDL weights for `complexity()`; placeholders (1.0) pending the kickoff Procrustes-scale calibration (Â§6 open-question #1; they only scale Î»Â·Complexity).
- **Protocol note (for sign-off):** `parameter_space()` declares only the *searched* scalar knobs; the *fitted* affine vectors live in Î¸ but cannot be expressed as `ParameterSpec` (it has no vector kind). This two-tier Î¸ (searched + fitted) is the plan's resolution (Â§3.1/Â§5) of the vector-ParameterSpec gap; the `transform-protocol` skill's "every Î¸ key in `parameter_space()`" invariant should be read as "every *searched* key."
- **Scores + exit-gate calibrator (Layer 4):** `scoring.py` â€” `simplicity_score` (1/(1+complexity/C_scale)) and `interpretability_score` (simplicity Â· family prior), reporting-only (never in the objective or gate). `baseline_thresholds.py` â€” `_unit_circle` (non-trivial null inscribed at max|coord|=0.5), `exit_thresholds` (per-letter `baseline_margin Â· d_circle`), and `evaluate_exit_gate` (aggregates a held-out distance table vs per-letter thresholds â†’ `ExitGateResult`: passed / accents_passed / letters_required / per-accent counts). New `models/exit_gate_result.py`. All pure â€” calibration constants are passed by the caller, so the Â§6 knobs (C_scale, priors, margin, fractions) are wired from config in Layer 5, not added here. **`mdl_complexity.py` deliberately not built:** the per-family `complexity()` already implements Complexity(F_Î¸) per Â§3, Â§6's unified-MDL/L(kind) form has no distinct consumer, and the lone coefficient-cost atom has a single caller (premature to extract). 15 tests.
- **SearchEngine (Layer 5):** `SearchEngine.fit` implemented as a standalone engine with `audio: Sequence[np.ndarray]`, one feature-matrix computation at fit entry, grid and continuous-only CMA-ES strategies, deterministic ParameterSpec decoding, grid overflow fail-loud/seeded-shuffle behavior, closed-form `FittableFamily.fit_theta` for Fourier and Lissajous, batched Fourier/Lissajous synthesis, batched Procrustes/Chamfer scoring, multi-stroke Chamfer substitution for ×”/×§, shared-vs-per-letter objective multiplier, candidate simplicity/interpretability scoring, and the standing `lookup_ratio` anti-lookup diagnostic. Lissajous was reparameterized to the linear `PÂ·sin(at)+QÂ·cos(at)` / `RÂ·sin(bt)` form required for least-squares fitting. `cma>=3.3.0` added as the runtime CMA-ES dependency; new config knobs added for grid/CMA/search scoring.
- **Data-contract change (maintainer-approved):** `TransformCandidate` gains `lookup_ratio: float`; mirrored in the scaffold ORM row and master plan Â§3.5.
- **Verified:** new modules pass at **100% coverage**, ruff clean â€” Layers 1â€“2: 34 tests; Layer 0+3: 45 tests; Layer 4: 15 tests; Layer 5: 85 focused tests.

### Deferred (flagged, not landed)

- **`release.yml` push-to-`main` model** under branch protection (audit #27): maintainer decision (bot-exempt / open-a-PR / tag-only). Only the Python-version alignment was applied.

### Notes

- **Version discrepancy (action required by maintainer):** `backend/pyproject.toml` reads `0.1.0` from an early `release: v0.1.0` tag, but the data pipeline does not yet run on real data, so the true pre-alpha version is **`0.0.1`** (next `0.0.2`). The version field + git tag are owned by the maintainer / release pipeline â€” reset `pyproject.toml` to `0.0.1` (or re-tag) at your discretion. This document and `status.md` reflect the intended `0.0.x` line.

---

## v0.0.1 â€” Initial scaffold + data decisions

### Decisions

- **Audio source = user-uploaded `.m4a` files only**, across five accents: `ashkenazi`, `sephardi`, `moroccan`, `yemenite`, `chabad`. No public-dataset ingester, no CLI recorder, no browser recorder. Master plan Â§11.1.
- **Generalization split = accent-disjoint**, leave-one-accent-out (5 rows). Master plan Â§11.3.
- **Glyph font = `StamAshkenazCLM.ttf`** (Culmus Project / Yoram Gnat / GPL v2). Committed at `backend/data/fonts/StamAshkenazCLM.ttf` alongside `StamAshkenazCLM.LICENSE.txt` and `StamAshkenazCLM.README.txt`. Master plan Â§11.2.
- **Scoring metric default = `procrustes_distance`**. FrÃ©chet and Chamfer are tiebreakers. Master plan Â§11.4.

### Added

- Full project scaffold per global `CLAUDE.md` Â§3
- Backend skeleton: FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + PyTorch + librosa + audioread + opencv + shapely + freetype-py, managed by `uv`
- `backend/src/simulation/transforms/` with the `TransformFamily` protocol and five placeholder families (Fourier series, Lissajous, phase-space embedding, dynamical system, symbolic regression)
- `backend/src/models/` with Pydantic models for AudioSample (including `accent`), GlyphTarget, PairedExample, TransformCandidate, ExperimentRun
- `constants.ACCENTS` vocabulary (`ashkenazi`, `sephardi`, `moroccan`, `yemenite`, `chabad`) with named string constants
- Vendored font: `backend/data/fonts/StamAshkenazCLM.ttf` (~15 KB, GPL v2) + license + README
- Mirrored ORM rows under `backend/src/data/orm/`
- Docker stack: postgres 16 + redis 7 + backend, with healthchecks and `depends_on: service_healthy` gating; ffmpeg in the backend image for `.m4a` decoding
- Launcher scripts: `run_audio_glyph_inference.{sh,bat}` with `[k]/[q]/[v]/[r]` loop
- Agent wiring: `.codex/hooks.json` (PreToolUse sensitive-file block, PostToolUse contextual reminders, Stop hooks); `.codex/commands/` (scaffold, review, pre-commit, validate, phase-status, new-transform-family); `.agents/skills/` (phase-awareness, transform-protocol, data-driven-check, validation-protocol, frontend-protocol). `CLAUDE.md` + `AGENTS.md` are kept in sync as the two harness entrypoints.
- `docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md` with full problem statement, data contracts, transform zoo, phase roadmap, Mermaid architecture + gantt + module-dependency diagrams, and Phase 1â€“5 gate checklists
- GitHub Actions (`.github/workflows/ci.yml` + `release.yml`) with lint â†’ test â†’ coverage-gate (100%) â†’ build â†’ docker-build stages and a manual release job

### Notes

- No logic implemented yet. All simulation methods raise `NotImplementedError`.
- The frontend (`frontend/` directory) is deliberately not scaffolded â€” it lands in Phase 4 per "non-applicable parts are removed, never stubbed."
