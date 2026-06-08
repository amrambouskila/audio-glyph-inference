"""baseline: audio_samples, glyph_targets, paired_examples

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-03

Phase-1 schema. The transform_candidates / experiment_runs tables are created
in a Phase-2 revision, not here.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "audio_samples",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("letter", sa.String(), nullable=False),
        sa.Column("speaker_id", sa.String(), nullable=False),
        sa.Column("accent", sa.String(), nullable=False),
        sa.Column("repetition", sa.Integer(), nullable=False),
        sa.Column("pronunciation_variant", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("sample_rate_hz", sa.Integer(), nullable=False),
        sa.Column("duration_s", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "speaker_id",
            "accent",
            "letter",
            "pronunciation_variant",
            "repetition",
            name="uq_audio_sample_take",
        ),
    )
    op.create_table(
        "glyph_targets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("letter", sa.String(), nullable=False),
        sa.Column("glyph_form", sa.String(), nullable=False),
        sa.Column("font_name", sa.String(), nullable=False),
        sa.Column("raster_size_px", sa.Integer(), nullable=False),
        sa.Column("contour_path", sa.String(), nullable=False),
        sa.Column("num_points", sa.Integer(), nullable=False),
        sa.Column("num_contours", sa.Integer(), nullable=False),
    )
    op.create_table(
        "paired_examples",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("audio_sample_id", sa.Uuid(), sa.ForeignKey("audio_samples.id"), nullable=False),
        sa.Column("glyph_target_id", sa.Uuid(), sa.ForeignKey("glyph_targets.id"), nullable=False),
        sa.Column("letter", sa.String(), nullable=False),
        sa.Column("pronunciation_variant", sa.String(), nullable=False),
        sa.Column("glyph_form", sa.String(), nullable=False),
        sa.Column("split", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("paired_examples")
    op.drop_table("glyph_targets")
    op.drop_table("audio_samples")
