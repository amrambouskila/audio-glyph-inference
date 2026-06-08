"""ParameterSpec — search-domain declaration for one θ component.

A transform family's `parameter_space()` returns one ParameterSpec per θ
key. The kind selects which fields are meaningful, so grid, CMA-ES, and
bayesian strategies can all derive their sampling from a single declaration:

  - 'continuous'  : low, high (float bounds)
  - 'integer'     : low, high (inclusive integer bounds, e.g. Fourier order K)
  - 'categorical' : choices (non-empty list, e.g. {'vanderpol', 'duffing'})
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator


class ParameterSpec(BaseModel):
    """Declarative search domain for a single transform parameter."""

    kind: Literal["continuous", "integer", "categorical"]
    low: float | None = None
    high: float | None = None
    choices: list[str] | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> ParameterSpec:
        if self.kind in ("continuous", "integer"):
            if self.low is None or self.high is None:
                raise ValueError(f"{self.kind} ParameterSpec requires both 'low' and 'high'")
            if self.high <= self.low:
                raise ValueError("ParameterSpec 'high' must exceed 'low'")
            if self.choices is not None:
                raise ValueError(f"{self.kind} ParameterSpec must not set 'choices'")
        else:
            if not self.choices:
                raise ValueError("categorical ParameterSpec requires a non-empty 'choices' list")
            if self.low is not None or self.high is not None:
                raise ValueError("categorical ParameterSpec must not set 'low'/'high'")
        return self
