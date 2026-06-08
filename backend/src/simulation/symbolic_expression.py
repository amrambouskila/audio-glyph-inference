"""Safe scalar expression evaluation for symbolic-regression candidates."""

from __future__ import annotations

import ast
import math
from collections.abc import Callable

import numpy as np

_FUNCTIONS: dict[str, Callable[[float], float]] = {
    "abs": abs,
    "cos": math.cos,
    "exp": math.exp,
    "log": math.log,
    "sin": math.sin,
    "sqrt": math.sqrt,
    "tanh": math.tanh,
}
_CONSTANTS = {"e": math.e, "pi": math.pi}


def evaluate_symbolic_expression(expression: str, features: np.ndarray) -> float:
    """Evaluate a safe scalar expression against an audio feature vector.

    Args:
        expression: expression string using constants pi/e, functions, and feature variables f0..fN.
        features: ndarray shape (D,) dtype=float64, units=audio feature space.

    Returns:
        finite scalar float expression value.
    """
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid symbolic expression {expression!r}") from exc
    try:
        value = _evaluate_node(parsed.body, features)
    except ArithmeticError as exc:
        raise ValueError(f"symbolic expression failed numerically: {expression!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"symbolic expression produced non-finite value: {expression!r}")
    return float(value)


def _evaluate_node(node: ast.AST, features: np.ndarray) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, int | float):
            return float(node.value)
        raise ValueError("symbolic expressions may contain only numeric constants")
    if isinstance(node, ast.Name):
        return _resolve_name(node.id, features)
    if isinstance(node, ast.UnaryOp):
        value = _evaluate_node(node.operand, features)
        if isinstance(node.op, ast.UAdd):
            return value
        if isinstance(node.op, ast.USub):
            return -value
    if isinstance(node, ast.BinOp):
        return _evaluate_binary(node, features)
    if isinstance(node, ast.Call):
        return _evaluate_call(node, features)
    raise ValueError(f"unsupported symbolic expression node {type(node).__name__}")


def _resolve_name(name: str, features: np.ndarray) -> float:
    if name in _CONSTANTS:
        return _CONSTANTS[name]
    if name.startswith("f") and name[1:].isdigit():
        index = int(name[1:])
        if index >= features.size:
            raise ValueError(f"feature variable {name!r} exceeds feature dimension {features.size}")
        return float(features[index])
    raise ValueError(f"unknown symbolic variable {name!r}")


def _evaluate_binary(node: ast.BinOp, features: np.ndarray) -> float:
    left = _evaluate_node(node.left, features)
    right = _evaluate_node(node.right, features)
    if isinstance(node.op, ast.Add):
        return left + right
    if isinstance(node.op, ast.Sub):
        return left - right
    if isinstance(node.op, ast.Mult):
        return left * right
    if isinstance(node.op, ast.Div):
        return left / right
    if isinstance(node.op, ast.Pow):
        return left**right
    raise ValueError(f"unsupported symbolic operator {type(node.op).__name__}")


def _evaluate_call(node: ast.Call, features: np.ndarray) -> float:
    if not isinstance(node.func, ast.Name):
        raise ValueError("symbolic function calls must be direct names")
    if node.keywords or len(node.args) != 1:
        raise ValueError("symbolic functions accept exactly one positional argument")
    try:
        function = _FUNCTIONS[node.func.id]
    except KeyError as exc:
        raise ValueError(f"unsupported symbolic function {node.func.id!r}") from exc
    return float(function(_evaluate_node(node.args[0], features)))
