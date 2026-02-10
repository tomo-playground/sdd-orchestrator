"""Standardize creative agent preset categories.

Revision ID: e5b2d6240c61
Revises: 2a131f2aaf2c
Create Date: 2026-02-10

Soft-deletes V1 debate presets and renames V2 categories to simpler names:
  v2_concept -> concept, v2_production -> production.
"""

from alembic import op

revision = "e5b2d6240c61"
down_revision = "2a131f2aaf2c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Soft-delete V1 debate presets
    op.execute(
        "UPDATE creative_agent_presets SET deleted_at = NOW() WHERE category = 'v1_debate' AND deleted_at IS NULL"
    )
    # 2. Rename v2_concept -> concept
    op.execute("UPDATE creative_agent_presets SET category = 'concept' WHERE category = 'v2_concept'")
    # 3. Rename v2_production -> production
    op.execute("UPDATE creative_agent_presets SET category = 'production' WHERE category = 'v2_production'")


def downgrade() -> None:
    # 1. Reverse category renames
    op.execute("UPDATE creative_agent_presets SET category = 'v2_concept' WHERE category = 'concept'")
    op.execute("UPDATE creative_agent_presets SET category = 'v2_production' WHERE category = 'production'")
    # 2. Un-soft-delete V1 debate presets
    op.execute(
        "UPDATE creative_agent_presets SET deleted_at = NULL WHERE category = 'v1_debate' AND deleted_at IS NOT NULL"
    )
