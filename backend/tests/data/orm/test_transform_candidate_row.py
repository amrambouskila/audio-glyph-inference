"""Tests for src/data/orm/transform_candidate_row.py."""

from __future__ import annotations

from src.data.orm.base import Base
from src.data.orm.transform_candidate_row import TransformCandidateRow


def test_transform_candidate_row_inherits_declarative_base() -> None:
    assert issubclass(TransformCandidateRow, Base)


def test_transform_candidate_row_tablename() -> None:
    assert TransformCandidateRow.__tablename__ == "transform_candidates"
