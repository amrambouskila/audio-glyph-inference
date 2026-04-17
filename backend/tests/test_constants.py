"""Tests for src/constants.py."""

from __future__ import annotations

import math

from src import constants


def test_math_constants_match_python_math_module() -> None:
    assert constants.PI == math.pi
    assert constants.TAU == 2.0 * math.pi
    assert constants.E == math.e
    assert math.isclose(constants.GOLDEN_RATIO, (1.0 + math.sqrt(5.0)) / 2.0)


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
