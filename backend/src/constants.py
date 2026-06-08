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
SQRT2: float = math.sqrt(2.0)  # unit-square diagonal; normalizes Chamfer/Fréchet distances

# --- Hebrew alphabet ---
# The 22 standard base letters of the Hebrew alef-bet, in canonical order.
# Used as the canonical base-letter label space for paired examples.
HEBREW_LETTERS: tuple[str, ...] = (
    "א",
    "ב",
    "ג",
    "ד",
    "ה",
    "ו",
    "ז",
    "ח",
    "ט",
    "י",
    "כ",
    "ל",
    "מ",
    "נ",
    "ס",
    "ע",
    "פ",
    "צ",
    "ק",
    "ר",
    "ש",
    "ת",
)

NUM_HEBREW_LETTERS: int = len(HEBREW_LETTERS)

# Sofit forms are written glyph variants, not separate audio labels.
SOFIT_GLYPH_FORMS: tuple[str, ...] = ("ך", "ם", "ן", "ף", "ץ")
GLYPH_FORMS: tuple[str, ...] = HEBREW_LETTERS + SOFIT_GLYPH_FORMS
NUM_GLYPH_FORMS: int = len(GLYPH_FORMS)

SOFIT_BASE_LETTER_BY_FORM: dict[str, str] = {
    "ך": "כ",
    "ם": "מ",
    "ן": "נ",
    "ף": "פ",
    "ץ": "צ",
}
BASE_LETTER_BY_GLYPH_FORM: dict[str, str] = {
    **{letter: letter for letter in HEBREW_LETTERS},
    **SOFIT_BASE_LETTER_BY_FORM,
}

# Traditional begadkefat letters recorded with explicit hard/soft variants.
BEGADKEFAT_LETTERS: tuple[str, ...] = ("ב", "ג", "ד", "כ", "פ", "ת")
PRONUNCIATION_VARIANT_PLAIN: str = "plain"
PRONUNCIATION_VARIANT_HARD: str = "hard"
PRONUNCIATION_VARIANT_SOFT: str = "soft"
PRONUNCIATION_VARIANTS: tuple[str, ...] = (
    PRONUNCIATION_VARIANT_PLAIN,
    PRONUNCIATION_VARIANT_HARD,
    PRONUNCIATION_VARIANT_SOFT,
)
PRONUNCIATION_VARIANTS_BY_BASE_LETTER: dict[str, tuple[str, ...]] = {
    letter: (
        (PRONUNCIATION_VARIANT_HARD, PRONUNCIATION_VARIANT_SOFT)
        if letter in BEGADKEFAT_LETTERS
        else (PRONUNCIATION_VARIANT_PLAIN,)
    )
    for letter in HEBREW_LETTERS
}
AUDIO_FORM_KEYS: tuple[tuple[str, str], ...] = tuple(
    (letter, variant) for letter in HEBREW_LETTERS for variant in PRONUNCIATION_VARIANTS_BY_BASE_LETTER[letter]
)
NUM_AUDIO_FORMS: int = len(AUDIO_FORM_KEYS)

# Letters whose STAM glyph has detached strokes in StamAshkenazCLM.ttf. Phase-2
# single-contour families score these flattened targets with Chamfer by default.
MULTI_STROKE_LETTERS: frozenset[str] = frozenset({"ה", "ק"})

# --- Accent vocabulary ---
# Controlled vocabulary for pronunciation traditions recorded by the user.
# Cross-accent generalization is the primary generalization test for this
# project (see docs/AUDIO_GLYPH_INFERENCE_MASTER_PLAN.md §11.3): we train
# on four accents and hold the fifth out (leave-one-accent-out across all
# five). Every AudioSample must be tagged with exactly one of these.
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

# --- Accepted upload MIME types ---
# Permissive allowlist for the .m4a (AAC-in-MP4) upload endpoint; see
# docs/recording_protocol.md §7. Tied to the format decision (§11.1), not
# environment-tunable.
ACCEPTED_AUDIO_MIME_TYPES: tuple[str, ...] = (
    "audio/mp4",
    "audio/x-m4a",
    "audio/aac",
)
