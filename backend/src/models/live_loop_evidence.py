"""LiveLoopEvidence - browser live-loop manual test evidence."""

from __future__ import annotations

from datetime import datetime
from math import isfinite
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.constants import GLYPH_FORMS


class LiveLoopEvidence(BaseModel):
    """Evidence from a manual all-glyph-form browser live-loop test."""

    tested_at: datetime = Field(description="Timestamp when the browser evidence was collected.")
    browser: str = Field(min_length=1, description="Browser and version used for the manual live-loop test.")
    candidate_id: UUID = Field(description="Transform candidate configured in the browser live-loop test.")
    score_rate_threshold_hz: float = Field(gt=0.0, description="Required minimum visible score update rate in Hz.")
    score_rate_hz_by_letter: dict[str, float] = Field(
        description="glyph form -> observed visible score update rate in Hz."
    )
    score_updates_by_letter: dict[str, int] = Field(description="glyph form -> counted score updates during the trial.")
    glyph_target_id_by_letter: dict[str, UUID] = Field(
        description="glyph form -> configured glyph target id echoed by backend."
    )
    visible_score_by_letter: dict[str, bool] = Field(description="glyph form -> whether the live score was visible.")

    @model_validator(mode="after")
    def _validate_all_letter_evidence(self) -> LiveLoopEvidence:
        expected_letters = set(GLYPH_FORMS)
        maps: tuple[tuple[str, dict[str, object]], ...] = (
            ("score_rate_hz_by_letter", self.score_rate_hz_by_letter),
            ("score_updates_by_letter", self.score_updates_by_letter),
            ("glyph_target_id_by_letter", self.glyph_target_id_by_letter),
            ("visible_score_by_letter", self.visible_score_by_letter),
        )
        for name, values in maps:
            if set(values) != expected_letters:
                raise ValueError(f"{name} must contain exactly constants.GLYPH_FORMS")
        for rate in self.score_rate_hz_by_letter.values():
            if not isfinite(rate) or rate < self.score_rate_threshold_hz:
                raise ValueError("live-loop score rates must be finite and meet the threshold")
        for updates in self.score_updates_by_letter.values():
            if updates <= 0:
                raise ValueError("live-loop score update counts must be positive")
        if not all(self.visible_score_by_letter.values()):
            raise ValueError("live-loop scores must be visible for every letter")
        return self
