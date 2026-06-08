const { emit, getToolFilePath, readHookPayload, toPosixPath } = require("./hookUtils.cjs");

const RULES = [
  {
    test: (p) => p.includes("/backend/src/simulation/transforms/"),
    context:
      "Transform family edited. Must implement TransformFamily protocol (name, parameter_space, forward). forward() returns ndarray shape (N,2) dtype=float64 in unit-square [-0.5, 0.5]. Parameters belong in parameter_space(), not as hard-coded literals.",
  },
  {
    test: (p) => p.includes("/backend/src/simulation/"),
    context:
      "Simulation code edited. Invariants: (1) engine must be importable standalone (no FastAPI / DB imports), (2) numpy arrays documented with shape+dtype+units, (3) no Python loops over frames in hot paths — vectorize or @numba.jit, (4) pytest file exists in backend/tests/simulation/ mirroring this path.",
  },
  {
    test: (p) => p.includes("/backend/src/data/orm/"),
    context:
      "ORM row edited. Must match the paired Pydantic model field-for-field (names + types) and be declared on src/data/orm/base.Base. Migration impact: add an alembic revision if this changes schema.",
  },
  {
    test: (p) => p.includes("/backend/src/models/"),
    context:
      "Pydantic model edited. This is a data contract. Do NOT silently change field names/types. Cross-check: (1) matching ORM row in backend/src/data/orm/, (2) matching test in backend/tests/models/, (3) docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md §3 data contracts still agrees.",
  },
];

async function main() {
  const payload = await readHookPayload();
  const f = toPosixPath(getToolFilePath(payload));
  if (!f) return;
  const m = RULES.find((r) => r.test(f));
  if (m) emit({ hookSpecificOutput: { hookEventName: "PostToolUse", additionalContext: m.context } });
}

main().catch((e) => {
  process.stderr.write(`[hook] post-tool-use failed: ${e.message}\n`);
  process.exitCode = 0;
});
