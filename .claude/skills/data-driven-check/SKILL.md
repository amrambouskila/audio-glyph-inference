---
name: data-driven-check
description: Proactively applied when writing any simulation, model, or API code; flags hard-coded domain values that should come from config or data
---

# Data-Driven Check

No hard-coded domain values. This is a standing rule — see global CLAUDE.md section 7 ("Data-driven, not hard-coded") and project CLAUDE.md §3.

## Protocol

Before finishing any code change, grep your diff for numeric literals and string literals. For each, ask:

1. Is it a **universal mathematical constant** (0, 1, 2, π, e)? OK — or, if named, move to `backend/src/constants.py`.
2. Is it an **array dimension or loop bound** derived from an input? OK.
3. Is it a **runtime parameter** (sample rate, frame length, raster size, contour point count, pipeline directory, font path)? → Must come from `backend/src/config.BackendSettings`. Add a field if missing. Never bake it in.
4. Is it a **transform parameter** (frequency, amplitude, phase, coupling strength)? → Must be an entry in the transform family's `parameter_space()` and passed via `theta`, not a literal in `forward()`.
5. Is it a **domain fact** (the 22 Hebrew letters, phoneme labels)? → Must live in `backend/src/constants.py` or a data file.

If a literal doesn't fit any of these categories and isn't in the OK list, it's a bug.

## Common misses

- `sample_rate = 16000` inside a preprocessing function → should be `config.audio_sample_rate_hz`.
- `if letter in "אבגדה..."` inline → should be `if letter in constants.HEBREW_LETTERS`.
- `font_path = "/app/data/fonts/StamAshkenazCLM.ttf"` inline → should be `config.font_file`.
- `num_contour_points = 256` inside `GlyphExtractor` default → should come from `config.glyph_contour_num_points`.