---
name: transform-protocol
description: Proactively applied when editing any file under backend/src/simulation/transforms/; enforces the TransformFamily contract
---

# Transform Protocol

Every file under `backend/src/simulation/transforms/` implements a `TransformFamily`. The protocol is sacred — violating it breaks every search and scoring run.

## The contract

```python
Theta = dict[str, float | int | list[float] | str]

class TransformFamily(Protocol):
    def name(self) -> str: ...
    def parameter_space(self) -> dict[str, ParameterSpec]: ...
    def complexity(self, theta: Theta) -> float: ...
    def forward(self, audio: np.ndarray, theta: Theta) -> np.ndarray: ...
```

### Invariants (verify before writing)

1. `name()` returns a unique string matching `TransformCandidate.family`.
2. `parameter_space()` contains every θ key referenced inside `forward()`. No undeclared parameters. Each value is a `ParameterSpec` (`continuous` / `integer` / `categorical`) declaring that key's search domain.
3. `complexity(theta)` returns the `Complexity(F_θ)` term of the §2 objective (lower is simpler) — typically an MDL-like cost from θ's cardinality. Pure function of `theta`.
4. `forward()` accepts:
   - `audio: ndarray` of shape `(num_frames, frame_length)`, dtype `float64`, preprocessed as documented in `simulation/audio_preprocessor.py`.
   - `theta: Theta` — only keys declared in `parameter_space()`; values may be `float | int | list[float] | str`.
5. `forward()` returns: `ndarray` of shape `(N, 2)`, dtype `float64`, unit-square coordinates in `[-0.5, 0.5]`. Any other shape/dtype/range is a bug.
6. `forward()` is a **pure function** — no globals, no file I/O, no RNG without a seeded `np.random.Generator`.
7. **No Python loops** over frames or parameters in the hot path. Vectorize with NumPy / SciPy / FFT, or wrap with `@numba.jit(nopython=True)`.

## When editing a transform

- Run through every invariant above before finishing.
- Ensure a matching test exists in `backend/tests/simulation/transforms/` and asserts the output shape/dtype/range contract.
- Do NOT add a `__init__` parameter that belongs in `parameter_space()`. Configuration (sample rate, raster size) comes from `config.BackendSettings` — never baked into the family.

## When adding a new family

Use `/new-transform-family`. Do not hand-roll the scaffold.