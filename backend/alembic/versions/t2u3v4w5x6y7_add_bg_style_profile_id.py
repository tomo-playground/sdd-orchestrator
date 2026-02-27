"""Add style_profile_id to backgrounds for style-aware caching

Phase 18-P3: StyleProfile 변경 시 stale 캐시 방지
- backgrounds.style_profile_id FK (SET NULL)
- Replace unique index (storyboard_id, location_key) with
  unique index (storyboard_id, location_key, style_profile_id)

Revision ID: t2u3v4w5x6y7
Revises: s1t2u3v4w5x6
Create Date: 2026-02-27 12:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "t2u3v4w5x6y7"
down_revision = "s1t2u3v4w5x6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "backgrounds",
        sa.Column(
            "style_profile_id",
            sa.Integer(),
            sa.ForeignKey("style_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Replace old 2-col unique index with new 3-col unique index
    op.drop_index("ix_backgrounds_storyboard_location_key", table_name="backgrounds")
    op.create_index(
        "ix_backgrounds_storyboard_location_style",
        "backgrounds",
        ["storyboard_id", "location_key", "style_profile_id"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND storyboard_id IS NOT NULL AND location_key IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("ix_backgrounds_storyboard_location_style", table_name="backgrounds")
    # Restore old 2-col unique index
    op.create_index(
        "ix_backgrounds_storyboard_location_key",
        "backgrounds",
        ["storyboard_id", "location_key"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND storyboard_id IS NOT NULL AND location_key IS NOT NULL"
        ),
    )
    op.drop_column("backgrounds", "style_profile_id")
