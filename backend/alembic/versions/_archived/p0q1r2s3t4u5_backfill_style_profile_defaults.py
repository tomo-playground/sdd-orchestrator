"""Backfill style_profile_id with system default.

Sets style_profile_id = (is_default=true profile) on projects, groups,
group_config, storyboards where currently NULL.

Revision ID: p0q1r2s3t4u5
Revises: o9p0q1r2s3t4
Create Date: 2026-02-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "p0q1r2s3t4u5"
down_revision: str = "o9p0q1r2s3t4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Backfill style_profile_id from is_default=true style profile
    op.execute("""
        UPDATE projects
        SET style_profile_id = (SELECT id FROM style_profiles WHERE is_default = true LIMIT 1)
        WHERE style_profile_id IS NULL
    """)

    op.execute("""
        UPDATE groups
        SET style_profile_id = (SELECT id FROM style_profiles WHERE is_default = true LIMIT 1)
        WHERE style_profile_id IS NULL
    """)

    op.execute("""
        UPDATE group_config
        SET style_profile_id = (SELECT id FROM style_profiles WHERE is_default = true LIMIT 1)
        WHERE style_profile_id IS NULL
    """)

    op.execute("""
        UPDATE storyboards
        SET style_profile_id = (SELECT id FROM style_profiles WHERE is_default = true LIMIT 1)
        WHERE style_profile_id IS NULL
    """)


def downgrade() -> None:
    # No-op: cannot distinguish original NULLs from backfilled values
    pass
