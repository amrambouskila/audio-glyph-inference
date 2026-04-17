"""Runtime configuration for the audio-glyph-inference backend.

All tunable parameters live here (Pydantic Settings) or in data files —
never as literals in logic. See global CLAUDE.md section 7.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    """Environment-driven backend configuration.

    Loaded from process environment; see `.env` at the project root for
    canonical variable names and defaults.
    """

    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_file=None,
        case_sensitive=False,
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    database_url: str = Field(
        default="postgresql+asyncpg://agi_dev:agi_dev_password@postgres:5432/audio_glyph_inference",
    )
    redis_url: str = "redis://redis:6379/0"

    audio_dir: Path = Path("/app/data/audio")
    font_file: Path = Path("/app/data/fonts/StamAshkenazCLM.ttf")
    contours_dir: Path = Path("/app/data/contours")
    experiments_dir: Path = Path("/app/experiments")

    audio_sample_rate_hz: int = 16_000
    audio_frame_length_samples: int = 512
    audio_hop_length_samples: int = 128

    glyph_raster_size_px: int = 256
    glyph_contour_num_points: int = 256


def get_settings() -> BackendSettings:
    """Return a fresh BackendSettings instance bound to the current env."""
    return BackendSettings()
