---
name: transform-protocol
description: Proactively applied when editing any file under backend/src/simulation/transforms/; enforces the TransformFamily contract
---

# Transform Protocol

Every file under `backend/src/simulation/transforms/` implements a `TransformFamily`. The protocol is sacred — violating it breaks every search and scoring run.

## The contract

```python
class TransformFamily(Protocol):
    def name(self) -> str: ...
    def parameter_space(self) -> dict[str, tuple[float, float]]: ...
    def forward(self, audio: np.ndarray, theta: dict[str, float]) -> np.ndarray: ...
```

### Invariants (verify before writing)

1. `name()` returns a unique string matching `TransformCandidate.family`.
2. `parameter_space()` contains every θ key referenced inside `forward()`. No undeclared parameters. Each value is `(low, high)` in the same units as the parameter itself.
3. `forward()` accepts:
   - `audio: ndarray` of shape `(num_frames, frame_length)`, dtype `float64`, preprocessed as documented in `simulation/audio_preprocessor.py`.
   - `theta: dict[str, float]` — only keys declared in `parameter_space()`.
4. `forward()` returns: `ndarray` of shape `(N, 2)`, dtype `float64`, unit-square coordinates in `[-0.5, 0.5]`. Any other shape/dtype/range is a bug.
5. `forward()` is a **pure function** — no globals, no file I/O, no RNG without a seeded `np.random.Generator`.
6. **No Python loops** over frames or parameters in the hot path. Vectorize with NumPy / SciPy / FFT, or wrap with `@numba.jit(nopython=True)`.

## When editing a transform

- Run through every invariant above before finishing.
- Ensure a matching test exists in `backend/tests/simulation/transforms/` and asserts the output shape/dtype/range contract.
- Do NOT add a `__init__` parameter that belongs in `parameter_space()`. Configuration (sample rate, raster size) comes from `config.BackendSettings` — never baked into the family.

## When adding a new family

Use `/new-transform-family`. Do not hand-roll the scaffold.