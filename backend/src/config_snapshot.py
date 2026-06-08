"""Flatten BackendSettings into a JSON-safe experiment snapshot."""

from __future__ import annotations

from src.config import BackendSettings


def config_snapshot(settings: BackendSettings) -> dict[str, str | int | float | bool]:
    """Return scalar BackendSettings values suitable for ExperimentRun.config_snapshot."""
    raw = settings.model_dump(mode="json")
    snapshot: dict[str, str | int | float | bool] = {}
    for key, value in raw.items():
        if isinstance(value, str | int | float | bool):
            snapshot[key] = value
        elif isinstance(value, list):
            snapshot[key] = ",".join(str(item) for item in value)
        else:
            snapshot[key] = str(value)
    return snapshot
