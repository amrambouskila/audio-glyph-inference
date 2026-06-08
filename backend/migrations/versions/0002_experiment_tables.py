"""experiment tables

Revision ID: 0002_experiment_tables
Revises: 0001_baseline
Create Date: 2026-06-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_experiment_tables"
down_revision: str | None = "0001_baseline"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "experiment_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("family", sa.String(), nullable=False),
        sa.Column("search_strategy", sa.String(), nullable=False),
        sa.Column("dataset_split", sa.String(), nullable=False),
        sa.Column("scoring_metric", sa.String(), nullable=False),
        sa.Column("regularization_weight", sa.Float(), nullable=False),
        sa.Column("held_out_accent", sa.String(), nullable=True),
        sa.Column("rng_seed", sa.Integer(), nullable=False),
        sa.Column("font_name", sa.String(), nullable=False),
        sa.Column("config_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("max_evaluations", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("best_candidate_id", sa.Uuid(), nullable=True),
    )
    op.create_table(
        "transform_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("family", sa.String(), nullable=False),
        sa.Column("theta", postgresql.JSONB(), nullable=False),
        sa.Column("expression", sa.String(), nullable=True),
        sa.Column("shared_across_letters", sa.Boolean(), nullable=False),
        sa.Column("interpretability_score", sa.Float(), nullable=False),
        sa.Column("simplicity_score", sa.Float(), nullable=False),
        sa.Column("mean_shape_distance", sa.Float(), nullable=False),
        sa.Column("lookup_ratio", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("transform_candidates")
    op.drop_table("experiment_runs")
