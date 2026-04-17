"""Registered transform families F_θ: audio -> 2D geometry.

Every family lives in its own module and implements the TransformFamily
protocol defined in transform_base.py. Families are discovered at import
time via the REGISTRY dict.
"""

from __future__ import annotations
