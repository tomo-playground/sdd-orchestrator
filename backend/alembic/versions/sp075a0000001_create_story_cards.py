"""SP-075: Create story_cards table

소재 카드 테이블 — 시리즈별 대본 소재 풀.
Research 노드가 미사용 소재를 Writer에 주입하여 대본 품질을 높인다.

Revision ID: sp075a0000001
Revises: sp020a0000001
Create Date: 2026-03-24
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "sp075a0000001"
down_revision = "sp020a0000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "story_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id", sa.Integer(), sa.ForeignKey("groups.id", ondelete="RESTRICT"), nullable=False, index=True
        ),
        sa.Column("cluster", sa.String(100), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="unused", index=True),
        sa.CheckConstraint("status IN ('unused', 'used', 'retired')", name="ck_story_cards_status"),
        sa.Column("situation", sa.Text(), nullable=True),
        sa.Column("hook_angle", sa.Text(), nullable=True),
        sa.Column("key_moments", postgresql.JSONB(), nullable=True),
        sa.Column("emotional_arc", postgresql.JSONB(), nullable=True),
        sa.Column("empathy_details", postgresql.JSONB(), nullable=True),
        sa.Column("characters_hint", postgresql.JSONB(), nullable=True),
        sa.Column("hook_score", sa.Float(), nullable=True),
        sa.Column(
            "used_in_storyboard_id",
            sa.Integer(),
            sa.ForeignKey("storyboards.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("story_cards")
