"""Runtime configuration for the audio-glyph-inference backend.

All tunable parameters live here (Pydantic Settings) or in data files —
never as literals in logic. See global CLAUDE.md section 7.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

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

    host: str = "0.0.0.0"  # noqa: S104 -- uvicorn must bind all interfaces inside the container; compose publishes the port
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

    # Audio-ingest validation + normalization thresholds (docs/recording_protocol.md §3/§7).
    audio_duration_min_s: float = 1.0
    audio_duration_max_s: float = 3.0
    audio_active_speech_min_s: float = 0.4
    audio_active_speech_max_s: float = 1.5
    audio_silence_pad_max_s: float = 0.3
    audio_peak_dbfs_max: float = -1.0
    audio_target_lufs: float = -23.0
    audio_vad_top_db: float = 30.0
    audio_default_speaker_id: str = "owner"
    audio_max_upload_bytes: int = 10_485_760

    glyph_raster_size_px: int = 256
    glyph_contour_num_points: int = 256

    # Phase-2 audio→feature extraction (docs/phases/phase-2-plan.md §2). Kept small +
    # transient-retaining (per-segment descriptors) so φ is not a clean phoneme label.
    feature_n_mels: int = 8
    feature_n_segments: int = 3

    # Phase-2 MDL complexity weights (docs/phases/phase-2-plan.md §6). Coefficients of
    # the Complexity(F_θ) term in the search objective; placeholders pending the kickoff
    # Procrustes-scale calibration (§6 open-question #1) — they only scale λ·Complexity.
    complexity_bits_per_param: float = 1.0
    complexity_order_penalty: float = 1.0
    complexity_struct_cost: float = 1.0

    # Phase-2 search knobs (docs/phases/phase-2-layer5-design.md §8). Calibration
    # defaults are frozen only after the first real-data Procrustes scale check.
    search_grid_resolution: int = 5
    search_grid_truncation: Literal["error", "seeded-shuffle"] = "error"
    search_log_scale_keys: frozenset[str] = frozenset({"ridge_alpha"})
    fourier_k_max: int = 3
    cma_sigma0: float = 0.25
    cma_tolfun: float = 1e-11
    bayesian_initial_points: int = Field(default=5, gt=0)
    bayesian_candidate_pool_size: int = Field(default=128, gt=0)
    bayesian_length_scale: float = Field(default=0.25, gt=0.0)
    bayesian_noise: float = Field(default=1e-9, gt=0.0)
    search_default_lambda: float = 0.01
    search_per_letter_penalty: float = 1.0
    simplicity_c_scale: float = 50.0
    interpretability_prior_fourier: float = 0.8
    interpretability_prior_lissajous: float = 1.0
    interpretability_prior_phase_space: float = 0.9
    interpretability_prior_symbolic: float = 0.7
    search_multistroke_metric: Literal["chamfer", "error"] = "chamfer"

    # Phase-3 symbolic-regression proposal path. PySR is optional because it
    # installs a Julia-backed search stack; saved symbolic candidates still run
    # without this extra.
    symbolic_fourier_k: int = 2
    symbolic_niterations: int = 20
    symbolic_maxsize: int = 20
    symbolic_binary_operators: list[str] = Field(default_factory=lambda: ["+", "-", "*", "/"])
    symbolic_unary_operators: list[str] = Field(default_factory=lambda: ["sin", "cos", "tanh"])
    symbolic_model_selection: Literal["accuracy", "best", "score"] = "best"


def get_settings() -> BackendSettings:
    """Return a fresh BackendSettings instance bound to the current env."""
    return BackendSettings()
