"""Tests for src/data/orm/paired_example_row.py."""

from __future__ import annotations

from src.data.orm.base import Base
from src.data.orm.paired_example_row import PairedExampleRow


def test_paired_example_row_inherits_declarative_base() -> None:
    assert issubclass(PairedExampleRow, Base)


def test_paired_example_row_tablename() -> None:
    assert PairedExampleRow.__tablename__ == "paired_examples"
