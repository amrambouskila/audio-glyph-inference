---
name: validation-protocol
description: Proactively applied when writing or modifying tests; enforces real assertions, reference values, and no-mocking rules
---

# Validation Protocol

Tests for this project are not style-box checks — they are what separates inferred structure from coincidence. Treat them accordingly.

## Rules

1. **No mocking of core math, no mocking of the database.** Numerical code is tested against real computations. Integration tests use a real Postgres via a test container. These are hard rules — see global CLAUDE.md §7 and project CLAUDE.md §7.
2. **Use `np.testing.assert_allclose(..., atol=..., rtol=...)` for float comparisons.** Never `==`. Document the tolerance in a comment if non-obvious.
3. **Every transform family has at least one reference-value test.** For example: a pure-tone sine at frequency f fed through the Lissajous family should produce an ellipse with known axis ratio — assert that. A randomly-generated audio signal matching the engine's own output is not a test; it's a tautology.
4. **Parametrize per letter with `@pytest.mark.parametrize`.** Every letter in `constants.HEBREW_LETTERS` should exercise the end-to-end pipeline at least once.
5. **Split and speaker tests.** At least one test must validate a candidate transform on a held-out speaker (cross-speaker generalization). A transform that only works on the speakers it was fitted to is not a discovery — it is an overfit.
6. **Coverage gate: 100%.** See `backend/pyproject.toml`'s `--cov-fail-under=100`. If coverage drops below, fix by adding tests, not by lowering the threshold.

## When reviewing a test

- Does it assert against a **published value** or a **closed-form analytical case**, or is it asserting against the engine's own output?
- Would a reasonable bug (off-by-one frame, swapped axes, missing √2) still make this test pass? If yes, it's a weak test.
- Does it test the **contract** (shape, dtype, range) separately from the **content** (the numeric answer)?

## Known pitfalls

- Floating-point comparisons with `==` — always use `assert_allclose`.
- Tests that "pass by construction" — generating the input from the output.
- Forgetting to parametrize over all 22 letters — finding a bug only on `ש` in production.