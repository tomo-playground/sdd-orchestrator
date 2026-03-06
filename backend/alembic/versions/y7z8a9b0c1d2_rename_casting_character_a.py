"""Rename casting_recommendation JSONB keys: character_id → character_a_id.

Revision ID: y7z8a9b0c1d2
Revises: x6y7z8a9b0c1
Create Date: 2026-03-06

JSONB 내부 키만 변경, 테이블 스키마 변경 없음.
"""

from alembic import op

revision = "y7z8a9b0c1d2"
down_revision = "f6c2e42b9449"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE storyboards
        SET casting_recommendation =
            (casting_recommendation - 'character_id' - 'character_name')
            || jsonb_build_object(
                'character_a_id', casting_recommendation->'character_id',
                'character_a_name', casting_recommendation->'character_name'
            )
        WHERE casting_recommendation ? 'character_id'
          AND NOT (casting_recommendation ? 'character_a_id')
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE storyboards
        SET casting_recommendation =
            (casting_recommendation - 'character_a_id' - 'character_a_name')
            || jsonb_build_object(
                'character_id', casting_recommendation->'character_a_id',
                'character_name', casting_recommendation->'character_a_name'
            )
        WHERE casting_recommendation ? 'character_a_id'
          AND NOT (casting_recommendation ? 'character_id')
    """)
