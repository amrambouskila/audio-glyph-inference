"""PairedExample — a single (audio, target glyph) training tuple.

This is the atomic unit of the dataset. All transform-family search runs
iterate over PairedExample instances, not raw AudioSample / GlyphTarget.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class PairedExample(BaseModel):
    """One training pair: spoken letter audio bound to its target glyph."""

    id: UUID
    audio_sample_id: UUID
    glyph_target_id: UUID
    letter: str
    split: str  # "train" | "val" | "test" — assigned per-speaker
