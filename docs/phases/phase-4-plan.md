# Phase 4 Plan — Live Pronunciation UI

**Goal.** An interactive browser tool: speak a letter, see the inferred geometry and score in real time.

**Entry gate.** Phase 3 complete (either a successful candidate or a documented negative result).

## In scope

- Scaffold `frontend/` for the first time (React 18 + TS strict + Vite + Zustand + `@react-three/fiber` + `@react-three/drei` + Chart.js + raw WebSocket + MessagePack) - implemented
- `frontend/Dockerfile` (multi-stage Node -> nginx) + `frontend/nginx.conf` - implemented
- Update `docker-compose.yml` to add the `frontend` service with `depends_on: { backend: { condition: service_healthy } }` - implemented
- Backend: `src/api/routers/live.py` implementing WebSocket `/ws/live` with MessagePack binary framing - implemented
- Audio capture in browser (`getUserMedia`), streamed to backend at the configured sample rate - implemented
- Backend streams back generated geometry and per-frame shape-distance score - implemented
- R3F scene: target glyph + generated contour overlaid, animated on each frame - implemented
- Chart.js score dashboard (history plus latest distance by letter plus score update rate) - implemented with focused component coverage
- Live UI catalog discovery for saved glyph targets and completed-run best candidates - implemented
- Vitest coverage of `src/utils/` - implemented
- CI frontend lint/unit-test/browser-smoke/build/docker-build wiring - implemented

## Explicitly deferred

- User accounts, persistence of user recordings
- Multi-user rooms

## Exit gate

- Full round-trip works for all 27 glyph forms
- Render rate ≥10 Hz end-to-end
- CI green (frontend: lint, unit test, browser smoke, build, docker-build)
