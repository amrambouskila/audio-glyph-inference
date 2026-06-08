"""Persistence for an ordered list of glyph stroke contours as a single .npz."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def save_contours(path: Path, contours: list[np.ndarray]) -> None:
    """Save ordered (n_i, 2) contours to a .npz under stable, sortable keys."""
    np.savez(path, **{f"c{i:03d}": contour for i, contour in enumerate(contours)})


def load_contours(path: Path) -> list[np.ndarray]:
    """Load the ordered contour list from a .npz produced by save_contours."""
    with np.load(path) as data:
        return [data[key] for key in sorted(data.files)]
