---
name: frontend-protocol
description: Proactively applied when editing frontend files (Phase 4+); enforces R3F disposal, Zustand state discipline, and the binary WebSocket contract
---

# Frontend Protocol

**This skill activates only in Phase 4+.** Phase 1 has no frontend — the `frontend/` directory does not exist yet. When P4 begins and `frontend/` is scaffolded, this protocol applies.

## Rules

1. **React state is for UI only.** Panel open/closed, selected letter, theme. Nothing else.
2. **Three.js / R3F objects never live in React or Zustand state.** They live in `useRef` or in the imperative render loop. Putting a `Mesh` in `useState` triggers reconciliation on every frame — fatal.
3. **Dispose geometry, materials, and textures when they leave the scene.** Three.js does not garbage-collect GPU resources. Use the R3F `useEffect(() => { return () => mesh.geometry.dispose(); }, [])` pattern.
4. **Instance and LOD where appropriate.** The live-pronunciation view renders the generated contour at high rate; use `InstancedMesh` for repeated primitives and LOD for distant content.
5. **Shaders live in `src/shaders/` as separate `.vert` / `.frag` files** — never inline template strings.
6. **Zustand stores own simulation state** (current letter, inferred contour, score history). One store per concern; no god stores.
7. **TypeScript strict, no `any`.** Prefer `interface` over `type` for object shapes.
8. **Binary over text for the live loop.** Audio frames and geometry updates go over WebSocket as MessagePack-framed binary. JSON only for metadata. See project CLAUDE.md §4 for the wire protocol.
9. **Chart.js for dashboards, d3 for bespoke, WebGL for 100k+ points.** Start at Chart.js. Move up only when chart types don't fit or volume demands it.
10. **Testing pitfalls (carry over from oft-frontend):**
    - Vitest doesn't auto-cleanup — `tests/setup.ts` must call `cleanup()` in `afterEach`.
    - Modal portals double in jsdom — use `within(screen.getByRole("dialog"))` to scope queries.
    - Title/button text collisions — use `{ selector: ".modal-title" }` vs `getByRole("button", { name })`.