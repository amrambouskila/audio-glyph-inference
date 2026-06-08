"""Tests for src/simulation/symbolic_expression.py."""

from __future__ import annotations

import math

import numpy as np
import pytest
from src.simulation.symbolic_expression import evaluate_symbolic_expression


def test_evaluate_symbolic_expression_closed_form() -> None:
    features = np.array([0.25, 0.5], dtype=np.float64)
    expression = "+sin(pi / 2) - cos(0) * tanh(f0) + sqrt(f1) + f1**2 - -e"
    actual = evaluate_symbolic_expression(expression, features)
    expected = math.sin(math.pi / 2.0) - math.cos(0.0) * math.tanh(0.25) + math.sqrt(0.5) + 0.5**2 - -math.e
    np.testing.assert_allclose(actual, expected, atol=1e-12)


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os')",
        "f2",
        "'text'",
        "min(f0)",
        "sin(f0, f1)",
        "sin(x=f0)",
        "(lambda x: x)(f0)",
        "f0 << 1",
        "unknown",
        "1 / 0",
        "log(-1)",
        "exp(10000)",
        "1e309",
        "1 +",
        "[f0]",
        "not f0",
    ],
)
def test_evaluate_symbolic_expression_rejects_unsafe_or_invalid_forms(expression: str) -> None:
    with pytest.raises(ValueError):
        evaluate_symbolic_expression(expression, np.array([1.0, 2.0], dtype=np.float64))
