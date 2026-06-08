# Completion Audit

This audit separates implemented repository work from empirical gates that require real recordings, saved candidates, and user-side live-loop testing. It does not claim Phase 5 completion.

## Summary

| Area | Status | Evidence | Remaining gate |
| --- | --- | --- | --- |
| Phase 1 data pipeline | Implemented; empirical data pass pending | Audio upload, preprocessing, glyph extraction, pairing, migrations, API tests, Docker image, launchers | Upload the planned 700 real `.m4a` recordings and reset the maintainer-owned package version from `0.1.0` to `0.0.1` before the real `0.1.0` release |
| Phase 2 baseline search | Implemented on approved contracts; empirical verdict pending | Shape metrics, transform families, SearchEngine, tracker/ORM, experiment/inference APIs, feasibility-probe core | Run calibration and exit-gate evaluation on Stage-7 recordings; optional status/provenance schema additions still require maintainer sign-off |
| Phase 3 expanded search | Implemented; final result pending | Dynamical-system family, Bayesian SearchEngine strategy, symbolic-regression conversion/proposal path, leave-one-accent-out harness, leaderboards, negative-results renderer | Run leave-one-accent-out experiments and populate real tables from experiment ledgers |
| Phase 4 live UI | Implemented; user-tested exit gate pending | MessagePack `/ws/live` with malformed-byte, non-string-map-key, malformed-configure-UUID, text-frame protocol-error handling, outbound finite-score validation, shared live/inference score-payload validation, configured candidate/glyph target echo validation, frontend microphone capture after confirmed configuration with successful-streaming/lifecycle cleanup, validated sample-rate env handling, outbound configure/audio encoder validation, failed-configure socket cleanup, audio-graph failure cleanup, socket-drop cleanup with active socket-error close, malformed-response cleanup, backend-error cleanup after streaming starts, finite-score parser hardening, socket-constructor failure guard, streaming reconfiguration cleanup, duplicate-start coverage, duplicate-connect guarding, configured-glyph score labeling, R3F overlay and Chart.js dashboard focused component coverage plus real-browser canvas smoke, catalog discovery, score-rate readout, recovered-error status preservation, Docker/CI wiring, non-empirical smoke-data seed command, all-glyph backend WebSocket smoke command | Test all 27 glyph forms in browser and confirm end-to-end update rate >=10 Hz; use real saved candidates for research claims |
| Phase 5 writeup | Prepared; empirical conclusion pending | `docs/writeup.md`, validated manifest, Stage-7 dataset audit command, validated result-artifact/live-loop-evidence models, all-glyph-form live-loop evidence template generator, notebook entrypoint with manifest transcript rendering and excluded-run-filtered leaderboard DataFrame prep, read-only report renderer, generated pending-data negative-results report | Replace pending-data scaffolds with real leaderboards, cross-accent tables, feasibility verdicts, and live-loop evidence |

## Current Verification Evidence

| Command | Status |
| --- | --- |
| `cd frontend && npm run lint` | Passed |
| `cd frontend && npm run test` | Passed; 47 tests, frontend utility/component coverage 100% |
| `cd frontend && npm run test:browser` | Passed; 2 Playwright Chromium smoke tests across desktop/mobile with R3F canvas pixel checks and visible `10.0 Hz` rate assertion |
| `cd frontend && npm run build` | Passed; Vite reports the expected large Three.js chunk warning |
| `cd backend && uv run pytest tests/scripts/test_smoke_live_roundtrip.py tests/scripts/test_seed_live_smoke.py --no-cov` | Passed; 9 focused script tests |
| `cd backend && uv run pytest tests/simulation/test_search_engine.py tests/test_config.py --no-cov` | Passed; 27 focused tests covering grid, CMA-ES, Bayesian search recovery/acquisition/zero-parameter cases, symbolic dispatch, and config defaults/env overrides |
| `cd backend && uv run pytest tests/scripts/test_audit_stage7_dataset.py --no-cov` | Passed; 7 focused tests covering complete, incomplete, extra, unpaired, mismatched audio/pair/glyph bindings, text output, JSON output, and invalid-manifest paths against real Postgres |
| `cd backend && uv run pytest tests/scripts/test_generate_live_loop_evidence_template.py tests/models/test_live_loop_evidence.py tests/scripts/test_render_phase5_report.py --no-cov` | Passed; focused tests covering the all-glyph-form live-loop evidence template, early CLI validation, intentionally-invalid placeholder evidence, evidence validation, Phase-5 report rendering, optional artifacts, invalid manifests, and visible non-empirical smoke-run exclusion |
| `cd backend && uv run pytest tests/models/test_exit_gate_result.py tests/models/test_feasibility_probe_result.py tests/models/test_leave_one_accent_out_result.py tests/scripts/test_render_phase5_report.py tests/simulation/test_leave_one_accent_out.py tests/simulation/test_negative_results.py --no-cov` | Passed previously; 26 focused tests covering Phase-5 result-artifact validation, manifest rendering, leave-one-accent-out reporting, and negative-results rendering |
| `cd backend && uv run ruff check .` | Passed |
| `cd backend && uv run ruff format --check .` | Passed |
| `cd backend && uv run pytest` | Passed; 426 passed, 1 host-ffmpeg smoke test skipped, backend coverage 100%; remaining warnings are codec-backend warnings on the optional `.m4a` smoke path |
| `cd backend && uv build` | Passed |
| `docker compose build` | Passed; backend and frontend images built; backend image was rebuilt after copying `scripts/` and setting `PYTHONPATH=/app` |
| `docker compose up -d` | Passed; Postgres, Redis, backend, and frontend start on documented ports |
| Host runtime checks | Passed; backend `/health` returns `{"status":"ok"}`, frontend `/` returns HTTP 200, and the smoke-seeded glyph catalog returns 22 rows |
| Launcher scripted control path | Passed; shell launcher handles invalid input then `k` via piped input, and batch launcher handles invalid input then `k` via `AGI_AUTO_CHOICES` with browser launch suppressed |
| Full verification refresh after launcher changes | Passed; backend lint/format/test/build and frontend lint/test/build rerun green |
| Source hygiene scan | Passed; implemented source has no `NotImplementedError`, TODO-style markers, or debug `print()` calls |
| Master-plan ingestion policy check | Passed; §11.1 matches `recording_protocol.md` and Decision #10: raw `.m4a` only, no `.wav` sidecar |
| Agent-entrypoint contract check | Passed; `AGENTS.md` and `CLAUDE.md` §8 match the current frozen fields for AudioSample, TransformCandidate, and ExperimentRun |
| Frontend API-contract check | Passed; `frontend/src/types/apiModels.ts` mirrors the backend API models, catalog summaries derive from it, and malformed array-shaped catalog payloads are rejected at the object-boundary parser |
| Generated-artifact ignore check | Passed; frontend coverage output is ignored by the root `.gitignore` |
| Live UI smoke-data seed path | Passed in Docker; `docker compose exec -T backend python scripts/seed_live_smoke.py` populates all 27 glyph targets plus one deterministic non-empirical candidate/run for browser round-trip testing |
| Live WebSocket smoke path | Passed against running Docker backend; MessagePack `configure` plus one PCM16 `audio` frame returned a `score` response with 256 generated and 256 target contour points |
| Live WebSocket malformed-message handling | Passed in focused backend tests; malformed MessagePack bytes return a binary protocol-error frame and the socket remains usable for subsequent messages |
| Live WebSocket text-frame handling | Passed in focused backend tests; text/non-binary WebSocket frames return a binary protocol-error frame and the socket remains usable |
| Live WebSocket map-key handling | Passed in focused backend tests; MessagePack maps with non-string keys return a binary protocol-error frame and the socket remains usable |
| Live WebSocket configure-UUID handling | Passed in focused backend tests; malformed configure UUID strings return a stable binary protocol-error frame and the socket remains usable |
| Live WebSocket outbound finite-score handling | Passed in focused backend tests; non-finite score distances and generated/target contour coordinates are rejected before MessagePack score serialization |
| Shared score-payload validation | Passed in focused backend tests; live score frames and one-shot inference responses share finite generated/target contour and `shape_distance` validation, and `/api/inference` returns 422 for malformed score geometry |
| Live configure-target echo validation | Passed in backend/frontend tests; backend `configured` frames echo candidate and glyph ids, frontend decoding requires both fields, mismatched glyph echoes close the socket before `CONNECTED`, and the all-glyph live smoke script validates the echoed pair |
| Live UI finite-score parsing | Passed in utility tests; non-finite score distances and generated/target contour coordinates are rejected before store/render updates |
| Live UI sample-rate env validation | Passed in utility tests; missing `VITE_AUDIO_SAMPLE_RATE_HZ` uses the documented live-loop default and malformed/non-positive/fractional values are rejected before audio capture or wire encoding |
| Live UI outbound encoder validation | Passed in utility tests; configure/audio MessagePack encoders reject empty ids, unknown metrics, invalid sample rates, and non-byte PCM payloads before serialization |
| Live UI seeded-catalog path | Passed in component test; the first fetched candidate/glyph is auto-selected and the Connect button becomes enabled without manual UUID entry |
| Live UI configure handshake | Passed in component tests; status waits for backend `configured`, and configure errors close the failed socket without requesting microphone access |
| Live UI microphone lifecycle path | Passed in component tests; successful microphone startup sends MessagePack PCM16 audio, stop disconnects processor/source, stops tracks, closes context, and closes socket, and unmount performs the same resource cleanup |
| Live UI duplicate-start guard | Passed in component test; rapid repeated Start microphone clicks while startup is in flight create only one socket, one media request, and one audio context |
| Live UI audio-graph failure cleanup | Passed in component test; if `AudioContext` setup fails after permission is granted, the stream track is stopped, the error is shown, and a later Start microphone retry can reach streaming |
| Live UI socket-drop cleanup | Passed in component tests; unexpected live WebSocket close/error during streaming disconnects processor/source, stops the media track, closes the audio context, actively closes the errored socket, and reports the socket closure/error |
| Live UI malformed-response cleanup | Passed in component test; malformed post-configuration binary responses disconnect processor/source, stop the media track, close the audio context, close the socket, clear the configured session, and return the UI to `idle` |
| Live UI backend-error cleanup | Passed in component test; backend `error` frames received after streaming starts disconnect processor/source, stop the media track, close the audio context, close the socket, clear the configured session, and return the UI to `idle` with the backend message still visible |
| Live UI streaming reconfiguration cleanup | Passed in component test; editing the candidate and pressing Connect while streaming releases the current audio graph, closes the old socket, and starts a new idle configure handshake |
| Live UI configured-letter score labeling | Passed in component test; after configuring a glyph target, changing the free-text Letter field does not mislabel subsequent score-history samples |
| Live UI duplicate-connect guard | Passed in component test; rapid repeated Connect clicks for the same candidate/glyph pair create one WebSocket and one configure frame |
| Live UI socket-constructor failure guard | Passed in component tests; Connect surfaces a browser WebSocket constructor failure, and Start microphone aborts without requesting microphone access when the live socket cannot be constructed |
| Live UI status-state hardening | Passed in store tests; clearing an error preserves connected/streaming status, setting an error moves to `error`, and accepting a score returns to `streaming` |
| Live UI R3F overlay coverage | Passed in component tests; target/generated lines are z-separated, styled distinctly, and singleton contours are suppressed |
| Live UI score-dashboard coverage | Passed in component tests; Chart.js line/bar datasets, per-letter latest-distance sorting, empty-history datasets, and responsive non-animated options are verified |
| Live UI browser canvas/rate smoke | Passed in Playwright; desktop/mobile Chromium render the real R3F canvas with nonblank generated/target pixels and a visible `10.0 Hz` rate readout after mocked MessagePack score frames |
| All-glyph live WebSocket smoke path | Passed in Docker; after `seed_live_smoke.py`, `smoke_live_roundtrip.py` configures and scores all 27 seeded glyph targets over `/ws/live` |
| Phase-5 manifest validation | Passed; renderer validates the committed pending-real-data manifest against the constants-backed sample plan, transform registry, ExperimentRun vocabularies, required target-font/writeup/notebook paths, and optional excluded run names before rendering |
| Stage-7 dataset audit | Passed in focused tests; `scripts/audit_stage7_dataset.py` reads the Phase-5 manifest repetitions, checks real Postgres audio/glyph/pair rows against constants-backed accents and Hebrew letters, reports missing/extra/unpaired takes plus mismatched audio/pair/glyph bindings, and exits non-zero until the dataset is complete |
| Phase-5 non-empirical ledger exclusion | Passed in focused tests; the pending-real-data manifest excludes `live-smoke-seed`, the generated report lists it under "Excluded Non-Empirical Runs", and deterministic browser-smoke JSONL ledgers do not appear in the leaderboard |
| Phase-5 result-artifact validation | Passed; leave-one-accent-out and feasibility-probe JSON artifacts reject unknown accents, non-canonical letters, non-finite metrics, negative distances, inconsistent accent maps, and out-of-scope exit-gate counts before report rendering |
| Phase-5 live-loop evidence validation | Passed in focused tests; optional browser evidence must cover exactly all glyph forms, visible scores, positive update counts, configured glyph ids, and score rates meeting the recorded threshold before report rendering |
| Phase-5 notebook reproducibility entrypoint | Passed in focused tests; the committed notebook imports the manifest renderer, builds leaderboard rows from `ExperimentTracker` / `build_family_leaderboards`, and applies manifest-declared `excluded_run_names` |
| Phase-5 read-only report rendering | Passed in focused tests; manifest rendering with a missing runs directory produces the empty-ledger report without creating the directory, while normal tracker construction still creates writeable run directories |
| Phase-5 live-loop evidence template | Passed in focused tests; the generator emits all four required maps over exactly `GLYPH_FORMS`, rejects malformed candidate UUIDs and non-positive score-rate thresholds at the CLI boundary, and writes/prints JSON for the user to fill with real browser observations |

## Maintainer-Owned Items

- Record and upload the Stage-7 dataset: 5 accents x 28 audio forms x 5 repetitions = 700 `.m4a` files.
- Decide whether to add the optional `ExperimentRunRow.status` and `TransformCandidateRow.experiment_run_id` schema fields.
- Reset `backend/pyproject.toml` from the premature `0.1.0` version back to `0.0.1`, using the maintainer-owned release workflow.
- Resolve the `release.yml` push-to-main model under branch protection.
- Run the browser live-loop pass; the smoke seed command can provide selectable rows before real searches exist, but real saved candidates are still required for any research claim.

## Repository-Ready Next Actions

1. When recordings exist, upload them through `POST /api/datasets/audio`, create glyph targets and pairs, then run `scripts/audit_stage7_dataset.py`.
2. Run the feasibility probe with calibrated `rho_min`.
3. Run Phase-2/3 searches over the real paired examples and write JSONL experiment ledgers through `ExperimentTracker`.
4. Render the Phase-5 report from the manifest and ledgers, then replace the pending-data sections in `docs/writeup.md` and `docs/negative-results.md`.
5. Use the Phase-4 UI to verify all 27 glyph forms and record the observed score-update rate.

## Non-Claims

- No successful operator has been claimed.
- No negative result has been claimed.
- No exit gate has been closed without real Stage-7 data.
- No data contract or schema change is authorized by this audit.
