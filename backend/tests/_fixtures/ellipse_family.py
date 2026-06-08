"""Shape-sensitive test TransformFamily for SearchEngine recovery tests."""

from __future__ import annotations

import numpy as np
from src.simulation.transforms.parameter_spec import ParameterSpec
from src.simulation.transforms.transform_base import Theta


class EllipseFamily:
    """Test family with one recoverable axis-ratio parameter."""

    def name(self) -> str:
        return "ellipse"

    def parameter_space(self) -> dict[str, ParameterSpec]:
        return {"b": ParameterSpec(kind="continuous", low=0.05, high=0.95)}

    def complexity(self, theta: Theta) -> float:
        return abs(float(theta["b"]))

    def forward(self, audio: np.ndarray, theta: Theta) -> np.ndarray:
        """Map ignored audio to an ellipse.

        Args:
            audio: ndarray (num_frames, frame_length) dtype=float64, ignored.
            theta: searched parameter dict containing b.

        Returns:
            ndarray (256, 2) dtype=float64, unit-square coordinates.
        """
        t = 2.0 * np.pi * np.arange(256) / 256
        return np.stack([0.5 * np.cos(t), float(theta["b"]) * np.sin(t)], axis=1).astype(np.float64)
