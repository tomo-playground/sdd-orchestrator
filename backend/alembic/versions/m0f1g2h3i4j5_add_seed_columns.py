"""Add seed columns to scenes and storyboards

Seed Anchoring (Phase 4):
- scenes.last_seed: SD API가 실제 사용한 seed 저장
- storyboards.base_seed: 스토리보드 전체의 기준 seed

Revision ID: m0f1g2h3i4j5
Revises: l9e0f1g2h3i4
Create Date: 2026-02-22 12:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "m0f1g2h3i4j5"
down_revision = "l9e0f1g2h3i4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scenes", sa.Column("last_seed", sa.BigInteger(), nullable=True))
    op.add_column("storyboards", sa.Column("base_seed", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("storyboards", "base_seed")
    op.drop_column("scenes", "last_seed")
