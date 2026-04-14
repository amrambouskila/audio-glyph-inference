"""Universal mathematical and physical constants for audio-glyph-inference.

Per global CLAUDE.md section 7 ("Data-driven, not hard-coded") this module
is the ONLY place for literal numbers that carry domain meaning. Everything
else (sampling rates, window sizes, glyph resolutions, font paths, search
hyperparameters) must come from config, the database, or data files.

Keep this file minimal. Add a constant here only if:
  - It is a genuinely universal mathematical/physical constant, AND
  - Hard-coding it anywhere else would be a policy violation.

If you find yourself reaching for a "constant" that describes a specific
audio pipeline, glyph extractor, or transform family, it belongs in a
Pydantic settings model, not here.
"""
from __future__ import annotations

import math

# --- Mathematical ---
PI: float = math.pi
TAU: float = 2.0 * math.pi
E: float = math.e
GOLDEN_RATIO: float = (1.0 + math.sqrt(5.0)) / 2.0

# --- Hebrew alphabet ---
# The 22 standard letters of the Hebrew alef-bet, in canonical order.
# Used as the canonical label space for paired examples. Final forms
# (sofit) are NOT added here — they share the same phoneme and are
# treated as visual variants handled at the glyph layer, not the audio
# layer. See docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md §3.1.
HEBREW_LETTERS: tuple[str, ...] = (
    "א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט", "י", "כ",
    "ל", "מ", "נ", "ס", "ע", "פ", "צ", "ק", "ר", "ש", "ת",
)

NUM_HEBREW_LETTERS: int = len(HEBREW_LETTERS)

# --- Accent vocabulary ---
# Controlled vocabulary for pronunciation traditions recorded by the user.
# Cross-accent generalization is the primary generalization test for this
# project (see docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md §11.3): we train
# on three accents and hold the fourth out. Every AudioSample must be
# tagged with exactly one of these.
ACCENT_ASHKENAZI: str = "ashkenazi"
ACCENT_SEPHARDI: str = "sephardi"
ACCENT_MOROCCAN: str = "moroccan"
ACCENT_YEMENITE: str = "yemenite"
ACCENT_CHABAD: str = "chabad"

ACCENTS: tuple[str, ...] = (
    ACCENT_ASHKENAZI,
    ACCENT_SEPHARDI,
    ACCENT_MOROCCAN,
    ACCENT_YEMENITE,
    ACCENT_CHABAD,
)

NUM_ACCENTS: int = len(ACCENTS)