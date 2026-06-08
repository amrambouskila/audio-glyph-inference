# Recording Protocol

Source of truth for how the project owner records Hebrew-letter audio samples, so that every sample is comparable across letters and accents and every `POST /api/datasets/audio` upload is reproducible.

> Read this before implementing `POST /api/datasets/audio` or `AudioPreprocessor.load` — the backend's validation and preprocessing choices follow from the decisions locked here. If anything in this doc is wrong, update it and propagate the change to `src/config.BackendSettings` and the dataset router's validation rules in the same commit.

---

## 1. What to say

**Say the Hebrew letter's NAME in the target accent, in isolation, with no leading or trailing word.** Not the phoneme, not a sample word containing the letter.

| Letter | Ashkenazi | Sephardi | Moroccan | Yemenite | Chabad |
|--------|-----------|----------|----------|----------|--------|
| א      | *alef*    | *alef*   | *alef*   | *alef*   | *alef* |
| ב      | *beis*    | *bet*    | *bet*    | *bet*    | *beis* |
| ...    | ...       | ...      | ...      | ...      | ...    |

The whole point of this project is that the acoustic realization of the letter name changes across accents. "Beis" vs "bet" vs "bet" (with a Moroccan uvular R coloring neighboring letters) vs "beith" (Yemenite emphatic) vs "beis" (Chabad, close to but not identical to generic Ashkenazi) — these are the signals `F_θ` must be robust to, or fail to be robust to (in which case we report that as the finding).

**Articulation rules:**
- Say the letter name, not a single phoneme. "alef", not a glottal stop in isolation.
- No carrier word. Don't say "the letter alef". Just "alef".
- No leading "uh" or clearing your throat.
- Consistent volume and distance across all samples in a session.
- One take per file. If you flub a repetition, delete the file and re-record — don't post-process.

If you want to change this policy (e.g. switch to single-phoneme recordings), update this section and the `AudioSample` docstring in the same commit, and note it in `docs/versions.md`.

---

## 2. Recording environment

- **Room.** Quiet, soft furnishings. No HVAC hum, no open windows, no background speech. A closet with clothes works well.
- **Microphone.** Any decent mic is fine — built-in laptop mic, AirPods, USB condenser, iPhone voice memos. **Use the same mic for the whole session**; don't mix mics within a single accent.
- **Distance.** ~15 cm (6 inches) from the mic. Don't breathe directly on it.
- **Format at the device.** AAC-in-MP4 (`.m4a`) — what iPhone Voice Memos and QuickTime produce natively. No transcoding on the client.
- **Sample rate at the device.** Whatever the device records at (typically 44.1 kHz or 48 kHz). The backend resamples to `config.audio_sample_rate_hz` (default 16 kHz) at ingest — do not resample on the client.
- **Channels.** Mono preferred. Stereo is fine; the backend will downmix.

---

## 3. Per-sample timing

| Quantity                  | Target                    | Enforced by                                              |
|---------------------------|---------------------------|----------------------------------------------------------|
| Total file duration       | 1.0 s to 3.0 s            | Server validation (reject outside range)                 |
| Leading silence           | ≤ 0.3 s                   | Server-side VAD trims                                    |
| Trailing silence          | ≤ 0.3 s                   | Server-side VAD trims                                    |
| Active speech duration    | 0.4 s to 1.5 s (post-trim)| Server validation (reject outside range)                 |
| Peak amplitude            | ≤ -1 dBFS                 | Server validation (reject clipped files)                 |
| Integrated loudness       | Normalized to -23 LUFS    | `pyloudnorm` during preprocessing (never rejected)       |

The server is lenient with loudness (it normalizes) but strict with clipping (it rejects). If you see "file rejected: clipped peak" when uploading, re-record with more headroom — loudness can always go up; clipping cannot be fixed.

---

## 4. Session structure

Record in **session blocks**, one block per `(accent, letter, pronunciation_variant)` audio form, with all N repetitions for that form recorded back-to-back in one sitting. This gives each `(accent, letter, pronunciation_variant, repetition)` a consistent intra-session tone.

**Default N = 5** (locked at the first recording session; change here if you adjust).

**Default session order:**
1. Pick one accent at a time. Finish all 28 audio forms × 5 repetitions = 140 files in that accent before moving on.
2. Within an accent, iterate through `constants.AUDIO_FORM_KEYS` order: 16 non-begadkefat `plain` forms plus hard/soft forms for `ב ג ד כ פ ת`.
3. Within an `(accent, letter, pronunciation_variant)` block, do all 5 repetitions without stopping.

A full dataset pass produces **5 accents × 28 audio forms × 5 repetitions = 700 `.m4a` files**.

Sofit forms (`ך ם ן ף ץ`) are written glyph forms only. They do not require separate audio recordings; the backend renders them through `POST /api/datasets/glyphs` with `glyph_form`.

You can do this in multiple sessions. `AudioSample.recorded_at` captures the timestamp; `AudioSample.source` stays `'user'`.

---

## 5. File naming on disk (pre-upload)

The endpoint takes `letter`, `accent`, `pronunciation_variant`, and `repetition` as form fields, so **filename is not load-bearing** — the server derives the storage path from the form fields, not the filename.

That said, for your own organization before upload, a recommended pattern is:

```
~/recordings/audio-glyph-inference/
├── ashkenazi/
│   ├── alef-01.m4a
│   ├── alef-02.m4a
│   ├── ...
│   ├── tav-05.m4a
├── sephardi/
│   └── ...
├── moroccan/
│   └── ...
├── yemenite/
│   └── ...
└── chabad/
    └── ...
```

Server-side, the canonical on-disk layout (created by the dataset router) is:

```
backend/data/audio/{accent}/{letter}/{pronunciation_variant}/{YYYY-MM-DD-HHMMSS}-rep{N}.m4a
```

Only the raw `.m4a` is persisted — it is the source of truth. The preprocessed (resampled, normalized, trimmed) signal is derived on demand by re-running `AudioPreprocessor` and is **not** written to disk in Phase 1 (no `.wav` sidecar, no `wav_path` field on `AudioSample` — Decision #10 = reconstruct-not-store). If the preprocessor policy changes, we re-run it — we don't re-record.

---

## 6. Upload workflow (Phase 1, once the endpoint is implemented)

For each file:

```bash
curl -X POST http://localhost:8220/api/datasets/audio \
  -F "file=@ashkenazi/alef-01.m4a" \
  -F "letter=א" \
  -F "accent=ashkenazi" \
  -F "pronunciation_variant=plain" \
  -F "repetition=1"
```

Response: `AudioSample` JSON with `id`, `letter`, `accent`, `pronunciation_variant`, `repetition`, `file_path` (the stored `.m4a`), `sample_rate_hz` (native), and `duration_s` (post-trim).

Batch uploads are a shell loop over the directory tree above. A helper script (`tools/upload_batch.sh` or similar) may be added during the Phase 1 batch-upload step — not yet decided whether as bash or a Python click CLI. Ask the user before building one.

---

## 7. What the server does with the upload

1. Validates `letter ∈ constants.HEBREW_LETTERS`, `accent ∈ constants.ACCENTS`, and `pronunciation_variant ∈ constants.PRONUNCIATION_VARIANTS_BY_BASE_LETTER[letter]` (422 otherwise).
2. Rejects if `repetition` is not a positive integer (422).
3. Checks file MIME type is `audio/mp4` / `audio/x-m4a` / `audio/aac` (415 otherwise).
4. Rejects if the upload exceeds `config.audio_max_upload_bytes` (413).
5. Writes the raw `.m4a` to `backend/data/audio/{accent}/{letter}/{pronunciation_variant}/{timestamp}-rep{N}.m4a`.
6. Runs `AudioPreprocessor.load`, which decodes (`librosa.load(sr=None)` → audioread → ffmpeg), validates duration ∈ [1.0, 3.0] s and peak ≤ -1 dBFS, resamples to 16 kHz, loudness-normalizes to -23 LUFS, VAD-trims, validates the active-speech span, and frames into `(num_frames, frame_length)`. A failed check raises `AudioValidationError` → 422 (and the stored `.m4a` is removed).
7. Inserts an `AudioSample` row (the `.m4a` path, the native sample rate, the post-trim duration, the `accent`, `pronunciation_variant`, `repetition`, and the owner `speaker_id`). A duplicate `(speaker_id, accent, letter, pronunciation_variant, repetition)` take → 409.
8. Returns the row as JSON.

The decode + validation + preprocessing (step 6) live in `AudioPreprocessor`; the router handles request validation, storage, persistence, and error mapping.

---

## 8. Test fixtures

For CI and local testing, commit a **single tiny `.m4a` fixture** (< 50 KB, ~1 s of silence + a synthetic tone) under `backend/tests/fixtures/test-sample.m4a`. This fixture is NOT real Hebrew audio — it exists only to exercise the real `.m4a` decode path when an ffmpeg/audioread backend is available. Real data lives in `backend/data/audio/` and is gitignored.

Endpoint integration tests use a soundfile-decodable synthetic upload payload with an accepted `.m4a` MIME type so `uv run pytest` stays self-contained on hosts without ffmpeg. The router still writes the payload to the canonical `.m4a` storage path and runs the real `AudioPreprocessor.load`, so storage, validation, persistence, cleanup, and duplicate-take branches remain covered. A separate preprocessor smoke test decodes the committed `.m4a` fixture when ffmpeg is available, and skips only that codec-specific check when the host has no backend.

---

## 9. What to do if a recording session goes sideways

- **Mic changed mid-session:** re-record the entire accent block. Don't mix mics.
- **Background noise appeared mid-session:** re-record from wherever noise started.
- **You realize you were saying the wrong letter name:** delete every file in that accent's block, re-record.
- **Phone battery died, files partially uploaded:** use the `GET /api/datasets/pairs?accent=X&letter=Y` endpoint to see what's already landed, delete those files locally, and upload the rest. Do not re-upload over existing rows.

---

## 10. Future changes to this protocol

If the protocol changes (duration range, loudness target, N per letter, articulation rule), update this doc **first**, then:
- `src/config.BackendSettings` for any numeric field
- `src/api/routers/datasets.py` for any validation rule
- `src/simulation/audio_preprocessor.AudioPreprocessor` for any preprocessing rule
- `docs/versions.md` with a one-line note

in the same commit. Never let the code and this doc drift.
