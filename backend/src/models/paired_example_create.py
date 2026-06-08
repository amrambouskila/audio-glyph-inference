"""PairedExampleCreate — request body for POST /api/datasets/pairs."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class PairedExampleCreate(BaseModel):
    """Associates an existing AudioSample with an existing GlyphTarget."""

    audio_sample_id: UUID
    glyph_target_id: UUID
    split: Literal["train", "val", "test"]
