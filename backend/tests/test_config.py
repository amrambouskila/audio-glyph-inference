"""Tests for src/config.py."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.config import BackendSettings, get_settings


def _clear_backend_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os_environ_keys()):
        if key.startswith("BACKEND_"):
            monkeypatch.delenv(key, raising=False)


def os_environ_keys() -> list[str]:
    import os

    return list(os.environ.keys())


def test_defaults_match_master_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_backend_env(monkeypatch)
    settings = BackendSettings()

    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.log_level == "info"
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.audio_dir == Path("/app/data/audio")
    assert settings.font_file == Path("/app/data/fonts/StamAshkenazCLM.ttf")
    assert settings.contours_dir == Path("/app/data/contours")
    assert settings.experiments_dir == Path("/app/experiments")
    assert settings.audio_sample_rate_hz == 16_000
    assert settings.audio_frame_length_samples == 512
    assert settings.audio_hop_length_samples == 128
    assert settings.glyph_raster_size_px == 256
    assert settings.glyph_contour_num_points == 256


def test_env_overrides_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_backend_env(monkeypatch)
    monkeypatch.setenv("BACKEND_PORT", "9090")
    monkeypatch.setenv("BACKEND_AUDIO_SAMPLE_RATE_HZ", "22050")
    monkeypatch.setenv("BACKEND_FONT_FILE", "/custom/font.ttf")

    settings = BackendSettings()

    assert settings.port == 9090
    assert settings.audio_sample_rate_hz == 22050
    assert settings.font_file == Path("/custom/font.ttf")


def test_env_prefix_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_backend_env(monkeypatch)
    monkeypatch.setenv("backend_host", "127.0.0.1")

    settings = BackendSettings()

    assert settings.host == "127.0.0.1"


def test_extra_env_vars_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_backend_env(monkeypatch)
    monkeypatch.setenv("BACKEND_UNKNOWN_SETTING", "whatever")

    BackendSettings()  # must not raise


def test_get_settings_returns_backend_settings_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_backend_env(monkeypatch)
    settings = get_settings()
    assert isinstance(settings, BackendSettings)


def test_get_settings_reflects_current_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_backend_env(monkeypatch)
    monkeypatch.setenv("BACKEND_LOG_LEVEL", "debug")
    assert get_settings().log_level == "debug"
