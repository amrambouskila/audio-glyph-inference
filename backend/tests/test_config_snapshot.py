"""Tests for src/config_snapshot.py."""

from __future__ import annotations

from pathlib import Path

from src.config import BackendSettings
from src.config_snapshot import config_snapshot


def test_config_snapshot_flattens_settings_values() -> None:
    settings = BackendSettings(
        font_file=Path("/tmp/font.ttf"),
        symbolic_binary_operators=["+", "*"],
        search_log_scale_keys=frozenset({"ridge_alpha"}),
    )

    snapshot = config_snapshot(settings)

    assert snapshot["font_file"] == str(Path("/tmp/font.ttf"))
    assert snapshot["symbolic_binary_operators"] == "+,*"
    assert snapshot["search_log_scale_keys"] == "ridge_alpha"
    assert snapshot["port"] == 8000
