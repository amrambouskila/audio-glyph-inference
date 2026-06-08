"""Tests for src/data/orm/transform_candidate_row.py."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from src.data.orm.base import Base
from src.data.orm.transform_candidate_row import TransformCandidateRow
from src.models.transform_candidate import TransformCandidate


def _row(**overrides) -> TransformCandidateRow:
    fields = {
        "id": uuid4(),
        "family": "fourier_series",
        "theta": {"rank_r": 1, "affine_b": [0.0, 1.0], "mode": "shared"},
        "expression": None,
        "shared_across_letters": True,
        "interpretability_score": 0.7,
        "simplicity_score": 0.8,
        "mean_shape_distance": 0.2,
        "lookup_ratio": 0.1,
        "created_at": datetime(2026, 4, 16, tzinfo=UTC),
    }
    fields.update(overrides)
    return TransformCandidateRow(**fields)


def test_transform_candidate_row_inherits_declarative_base() -> None:
    assert issubclass(TransformCandidateRow, Base)


def test_transform_candidate_row_tablename() -> None:
    assert TransformCandidateRow.__tablename__ == "transform_candidates"


def test_transform_candidate_row_columns_match_model_contract() -> None:
    assert set(TransformCandidateRow.__table__.columns.keys()) == {
        "id",
        "family",
        "theta",
        "expression",
        "shared_across_letters",
        "interpretability_score",
        "simplicity_score",
        "mean_shape_distance",
        "lookup_ratio",
        "created_at",
    }


async def test_transform_candidate_row_round_trips(db_session) -> None:
    row = _row(expression="sin(t)")
    db_session.add(row)
    await db_session.commit()

    fetched = (
        await db_session.execute(select(TransformCandidateRow).where(TransformCandidateRow.id == row.id))
    ).scalar_one()
    model = TransformCandidate.model_validate(fetched)

    assert model.family == "fourier_series"
    assert model.theta["affine_b"] == [0.0, 1.0]
    assert model.expression == "sin(t)"
    assert model.lookup_ratio == 0.1
