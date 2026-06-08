"""FastAPI dependencies — per-request DB session + config-built engines."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import BackendSettings
from src.data.database import create_session_factory
from src.simulation.audio_preprocessor import AudioPreprocessor
from src.simulation.experiment_tracker import ExperimentTracker
from src.simulation.glyph_extractor import GlyphExtractor


def get_settings_dep(request: Request) -> BackendSettings:
    """The BackendSettings stored on the app at creation."""
    return request.app.state.settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a per-request AsyncSession; endpoints commit explicitly."""
    factory = create_session_factory(request.app.state.engine)
    async with factory() as session:
        yield session


def get_audio_preprocessor(request: Request) -> AudioPreprocessor:
    """Build an AudioPreprocessor from the app's settings."""
    settings: BackendSettings = request.app.state.settings
    return AudioPreprocessor(
        target_sample_rate_hz=settings.audio_sample_rate_hz,
        frame_length_samples=settings.audio_frame_length_samples,
        hop_length_samples=settings.audio_hop_length_samples,
        duration_min_s=settings.audio_duration_min_s,
        duration_max_s=settings.audio_duration_max_s,
        active_speech_min_s=settings.audio_active_speech_min_s,
        active_speech_max_s=settings.audio_active_speech_max_s,
        peak_dbfs_max=settings.audio_peak_dbfs_max,
        target_lufs=settings.audio_target_lufs,
        vad_top_db=settings.audio_vad_top_db,
    )


def get_glyph_extractor(request: Request) -> GlyphExtractor:
    """Build a GlyphExtractor from the app's settings (opens the font)."""
    settings: BackendSettings = request.app.state.settings
    return GlyphExtractor(
        font_path=settings.font_file,
        raster_size_px=settings.glyph_raster_size_px,
        num_contour_points=settings.glyph_contour_num_points,
    )


def get_experiment_tracker(request: Request) -> ExperimentTracker:
    """Build the JSONL experiment tracker from settings."""
    settings: BackendSettings = request.app.state.settings
    return ExperimentTracker(settings.experiments_dir)
