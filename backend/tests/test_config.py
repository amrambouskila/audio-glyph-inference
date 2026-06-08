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
    assert settings.audio_duration_min_s == 1.0
    assert settings.audio_duration_max_s == 3.0
    assert settings.audio_active_speech_min_s == 0.4
    assert settings.audio_active_speech_max_s == 1.5
    assert settings.audio_silence_pad_max_s == 0.3
    assert settings.audio_peak_dbfs_max == -1.0
    assert settings.audio_target_lufs == -23.0
    assert settings.audio_vad_top_db == 30.0
    assert settings.audio_default_speaker_id == "owner"
    assert settings.audio_max_upload_bytes == 10_485_760
    assert settings.glyph_raster_size_px == 256
    assert settings.glyph_contour_num_points == 256
    assert settings.feature_n_mels == 8
    assert settings.feature_n_segments == 3
    assert settings.complexity_bits_per_param == 1.0
    assert settings.complexity_order_penalty == 1.0
    assert settings.complexity_struct_cost == 1.0
    assert settings.search_grid_resolution == 5
    assert settings.search_grid_truncation == "error"
    assert settings.search_log_scale_keys == frozenset({"ridge_alpha"})
    assert settings.fourier_k_max == 3
    assert settings.cma_sigma0 == 0.25
    assert settings.cma_tolfun == 1e-11
    assert settings.bayesian_initial_points == 5
    assert settings.bayesian_candidate_pool_size == 128
    assert settings.bayesian_length_scale == 0.25
    assert settings.bayesian_noise == 1e-9
    assert settings.search_default_lambda == 0.01
    assert settings.search_per_letter_penalty == 1.0
    assert settings.simplicity_c_scale == 50.0
    assert settings.interpretability_prior_fourier == 0.8
    assert settings.interpretability_prior_lissajous == 1.0
    assert settings.interpretability_prior_phase_space == 0.9
    assert settings.interpretability_prior_symbolic == 0.7
    assert settings.search_multistroke_metric == "chamfer"
    assert settings.symbolic_fourier_k == 2
    assert settings.symbolic_niterations == 20
    assert settings.symbolic_maxsize == 20
    assert settings.symbolic_binary_operators == ["+", "-", "*", "/"]
    assert settings.symbolic_unary_operators == ["sin", "cos", "tanh"]
    assert settings.symbolic_model_selection == "best"


def test_env_overrides_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_backend_env(monkeypatch)
    monkeypatch.setenv("BACKEND_PORT", "9090")
    monkeypatch.setenv("BACKEND_AUDIO_SAMPLE_RATE_HZ", "22050")
    monkeypatch.setenv("BACKEND_FONT_FILE", "/custom/font.ttf")
    monkeypatch.setenv("BACKEND_AUDIO_TARGET_LUFS", "-20.0")
    monkeypatch.setenv("BACKEND_AUDIO_MAX_UPLOAD_BYTES", "5242880")
    monkeypatch.setenv("BACKEND_SEARCH_GRID_RESOLUTION", "7")
    monkeypatch.setenv("BACKEND_SEARCH_DEFAULT_LAMBDA", "0.03")
    monkeypatch.setenv("BACKEND_SEARCH_MULTISTROKE_METRIC", "error")
    monkeypatch.setenv("BACKEND_BAYESIAN_INITIAL_POINTS", "3")
    monkeypatch.setenv("BACKEND_BAYESIAN_CANDIDATE_POOL_SIZE", "16")
    monkeypatch.setenv("BACKEND_SYMBOLIC_FOURIER_K", "1")
    monkeypatch.setenv("BACKEND_SYMBOLIC_NITERATIONS", "4")

    settings = BackendSettings()

    assert settings.port == 9090
    assert settings.audio_sample_rate_hz == 22050
    assert settings.font_file == Path("/custom/font.ttf")
    assert settings.audio_target_lufs == -20.0
    assert settings.audio_max_upload_bytes == 5_242_880
    assert settings.search_grid_resolution == 7
    assert settings.search_default_lambda == 0.03
    assert settings.search_multistroke_metric == "error"
    assert settings.bayesian_initial_points == 3
    assert settings.bayesian_candidate_pool_size == 16
    assert settings.symbolic_fourier_k == 1
    assert settings.symbolic_niterations == 4


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
