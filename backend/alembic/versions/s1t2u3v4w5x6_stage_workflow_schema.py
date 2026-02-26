"""Stage Workflow: backgrounds.storyboard_id/location_key + storyboards.stage_status

Phase 18-0: Location Model + DB
- backgrounds: storyboard_id FK (CASCADE) + location_key for per-storyboard backgrounds
- storyboards: stage_status for staging pipeline state
- Partial unique index on (storyboard_id, location_key) to prevent duplicates

Revision ID: s1t2u3v4w5x6
Revises: r5k6l7m8n9o0
Create Date: 2026-02-26 18:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "s1t2u3v4w5x6"
down_revision = "r5k6l7m8n9o0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- backgrounds table ---
    op.add_column(
        "backgrounds",
        sa.Column("storyboard_id", sa.Integer(), sa.ForeignKey("storyboards.id", ondelete="CASCADE"), nullable=True),
    )
    op.add_column(
        "backgrounds",
        sa.Column("location_key", sa.String(100), nullable=True),
    )
    op.create_index("ix_backgrounds_storyboard_id", "backgrounds", ["storyboard_id"])
    op.create_index(
        "ix_backgrounds_storyboard_location_key",
        "backgrounds",
        ["storyboard_id", "location_key"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND storyboard_id IS NOT NULL AND location_key IS NOT NULL"),
    )

    # --- storyboards table ---
    op.add_column(
        "storyboards",
        sa.Column("stage_status", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("storyboards", "stage_status")
    op.drop_index("ix_backgrounds_storyboard_location_key", table_name="backgrounds")
    op.drop_index("ix_backgrounds_storyboard_id", table_name="backgrounds")
    op.drop_column("backgrounds", "location_key")
    op.drop_column("backgrounds", "storyboard_id")
