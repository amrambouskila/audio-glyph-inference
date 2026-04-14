# Phase 4 Plan — Live Pronunciation UI

**Goal.** An interactive browser tool: speak a letter, see the inferred geometry and score in real time.

**Entry gate.** Phase 3 complete (either a successful candidate or a documented negative result).

## In scope

- Scaffold `frontend/` for the first time (React 18 + TS strict + Vite + Zustand + `@react-three/fiber` + `@react-three/drei` + Chart.js + `socket.io-client`)
- `frontend/Dockerfile` (multi-stage Node → nginx) + `frontend/nginx.conf`
- Update `docker-compose.yml` to add the `frontend` service with `depends_on: { backend: { condition: service_healthy } }`
- Backend: `src/api/routers/live.py` implementing WebSocket `/ws/live` with MessagePack binary framing
- Audio capture in browser (`getUserMedia`), streamed to backend at 16 kHz
- Backend streams back generated geometry and per-frame shape-distance score
- R3F scene: target glyph + generated contour overlaid, animated on each frame
- Chart.js score dashboard (history, per-letter distribution)
- Vitest + React Testing Library coverage of `src/utils/`

## Explicitly deferred

- User accounts, persistence of user recordings
- Multi-user rooms

## Exit gate

- Full round-trip works for all 22 letters
- Render rate ≥10 Hz end-to-end
- CI green (frontend: lint, test, build, docker-build)