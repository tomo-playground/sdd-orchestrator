"""schema_cleanup_batch_b_types

Revision ID: q1r2s3t4u5v6
Revises: p0q1r2s3t4u5
Create Date: 2026-02-04

Batch B: Type corrections
- scenes.use_reference_only: Integer -> Boolean
- storyboards.recent_videos_json: Text -> JSONB + rename to recent_videos
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "q1r2s3t4u5v6"
down_revision = "p0q1r2s3t4u5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # scenes: Integer -> Boolean (drop old default first to avoid cast error)
    op.alter_column("scenes", "use_reference_only", server_default=None)
    op.alter_column(
        "scenes",
        "use_reference_only",
        type_=sa.Boolean(),
        postgresql_using="CASE WHEN use_reference_only = 1 THEN TRUE ELSE FALSE END",
    )
    op.alter_column("scenes", "use_reference_only", server_default=sa.text("true"))

    # storyboards: Text -> JSONB + rename
    op.alter_column(
        "storyboards",
        "recent_videos_json",
        type_=postgresql.JSONB(),
        postgresql_using="recent_videos_json::jsonb",
    )
    op.alter_column(
        "storyboards",
        "recent_videos_json",
        new_column_name="recent_videos",
    )


def downgrade() -> None:
    # Reverse rename
    op.alter_column(
        "storyboards",
        "recent_videos",
        new_column_name="recent_videos_json",
    )

    # JSONB -> Text
    op.alter_column(
        "storyboards",
        "recent_videos_json",
        type_=sa.Text(),
        postgresql_using="recent_videos_json::text",
    )

    # Boolean -> Integer (drop default first to avoid cast error)
    op.alter_column("scenes", "use_reference_only", server_default=None)
    op.alter_column(
        "scenes",
        "use_reference_only",
        type_=sa.Integer(),
        postgresql_using="CASE WHEN use_reference_only THEN 1 ELSE 0 END",
    )
    op.alter_column("scenes", "use_reference_only", server_default=sa.text("1"))
