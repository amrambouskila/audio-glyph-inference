"""Tests for src/constants.py."""

from __future__ import annotations

import math

from src import constants


def test_math_constants_match_python_math_module() -> None:
    assert constants.PI == math.pi
    assert constants.TAU == 2.0 * math.pi
    assert constants.E == math.e
    assert math.isclose(constants.GOLDEN_RATIO, (1.0 + math.sqrt(5.0)) / 2.0)
    assert constants.SQRT2 == math.sqrt(2.0)


def test_hebrew_letters_has_exactly_22_entries() -> None:
    assert len(constants.HEBREW_LETTERS) == 22
    assert constants.NUM_HEBREW_LETTERS == 22


def test_hebrew_letters_are_unique() -> None:
    assert len(set(constants.HEBREW_LETTERS)) == len(constants.HEBREW_LETTERS)


def test_hebrew_letters_in_canonical_order() -> None:
    expected = (
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
    assert constants.HEBREW_LETTERS == expected


def test_hebrew_letters_immutable() -> None:
    assert isinstance(constants.HEBREW_LETTERS, tuple)


def test_glyph_forms_include_regular_and_sofit_forms() -> None:
    assert constants.SOFIT_GLYPH_FORMS == ("ך", "ם", "ן", "ף", "ץ")
    assert constants.GLYPH_FORMS == constants.HEBREW_LETTERS + constants.SOFIT_GLYPH_FORMS
    assert constants.NUM_GLYPH_FORMS == 27
    assert len(set(constants.GLYPH_FORMS)) == constants.NUM_GLYPH_FORMS


def test_sofit_forms_map_to_base_letters() -> None:
    assert constants.SOFIT_BASE_LETTER_BY_FORM == {
        "ך": "כ",
        "ם": "מ",
        "ן": "נ",
        "ף": "פ",
        "ץ": "צ",
    }
    for letter in constants.HEBREW_LETTERS:
        assert constants.BASE_LETTER_BY_GLYPH_FORM[letter] == letter
    assert constants.BASE_LETTER_BY_GLYPH_FORM["ך"] == "כ"


def test_pronunciation_variants_expand_begadkefat_audio_forms() -> None:
    assert constants.BEGADKEFAT_LETTERS == ("ב", "ג", "ד", "כ", "פ", "ת")
    assert constants.PRONUNCIATION_VARIANTS == ("plain", "hard", "soft")
    for letter in constants.BEGADKEFAT_LETTERS:
        assert constants.PRONUNCIATION_VARIANTS_BY_BASE_LETTER[letter] == ("hard", "soft")
    assert constants.PRONUNCIATION_VARIANTS_BY_BASE_LETTER["א"] == ("plain",)
    assert constants.NUM_AUDIO_FORMS == 28
    assert len(constants.AUDIO_FORM_KEYS) == constants.NUM_AUDIO_FORMS
    assert ("ב", "hard") in constants.AUDIO_FORM_KEYS
    assert ("ב", "soft") in constants.AUDIO_FORM_KEYS
    assert ("ב", "plain") not in constants.AUDIO_FORM_KEYS


def test_multi_stroke_letters_are_known_hebrew_letters() -> None:
    assert constants.MULTI_STROKE_LETTERS == frozenset({"ה", "ק"})
    assert constants.MULTI_STROKE_LETTERS.issubset(constants.HEBREW_LETTERS)


def test_accents_vocabulary_matches_master_plan() -> None:
    assert constants.ACCENTS == (
        constants.ACCENT_ASHKENAZI,
        constants.ACCENT_SEPHARDI,
        constants.ACCENT_MOROCCAN,
        constants.ACCENT_YEMENITE,
        constants.ACCENT_CHABAD,
    )
    assert constants.ACCENTS == (
        "ashkenazi",
        "sephardi",
        "moroccan",
        "yemenite",
        "chabad",
    )
    assert constants.NUM_ACCENTS == 5


def test_accents_are_unique_and_immutable() -> None:
    assert len(set(constants.ACCENTS)) == len(constants.ACCENTS)
    assert isinstance(constants.ACCENTS, tuple)


def test_accepted_audio_mime_types() -> None:
    assert isinstance(constants.ACCEPTED_AUDIO_MIME_TYPES, tuple)
    assert "audio/mp4" in constants.ACCEPTED_AUDIO_MIME_TYPES
    assert len(set(constants.ACCEPTED_AUDIO_MIME_TYPES)) == len(constants.ACCEPTED_AUDIO_MIME_TYPES)
