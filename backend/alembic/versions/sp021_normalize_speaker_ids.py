"""SP-021: Normalize speaker IDs (A→speaker_1, B→speaker_2, Narrator→narrator)

Revision ID: sp021a1b2c3d4
Revises: z8a9b0c1d2e3
Create Date: 2026-03-24

Data-only migration: no schema changes, only UPDATE statements.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "sp021a1b2c3d4"
down_revision = "sp020a0000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # scenes.speaker 데이터 변환 (soft-deleted rows 포함 — 이력 데이터 일관성)
    op.execute("UPDATE scenes SET speaker = 'speaker_1' WHERE speaker = 'A'")
    op.execute("UPDATE scenes SET speaker = 'speaker_2' WHERE speaker = 'B'")
    op.execute("UPDATE scenes SET speaker = 'narrator' WHERE speaker = 'Narrator'")

    # scenes.speaker server_default 동기화
    op.alter_column(
        "scenes",
        "speaker",
        server_default="narrator",
        existing_type=sa.String(20),
        existing_nullable=True,
    )

    # storyboard_characters.speaker 데이터 변환
    op.execute("UPDATE storyboard_characters SET speaker = 'speaker_1' WHERE speaker = 'A'")
    op.execute("UPDATE storyboard_characters SET speaker = 'speaker_2' WHERE speaker = 'B'")


def downgrade() -> None:
    op.execute("UPDATE scenes SET speaker = 'A' WHERE speaker = 'speaker_1'")
    op.execute("UPDATE scenes SET speaker = 'B' WHERE speaker = 'speaker_2'")
    op.execute("UPDATE scenes SET speaker = 'Narrator' WHERE speaker = 'narrator'")

    # server_default 원복
    op.alter_column(
        "scenes",
        "speaker",
        server_default="Narrator",
        existing_type=sa.String(20),
        existing_nullable=True,
    )

    op.execute("UPDATE storyboard_characters SET speaker = 'A' WHERE speaker = 'speaker_1'")
    op.execute("UPDATE storyboard_characters SET speaker = 'B' WHERE speaker = 'speaker_2'")
    op.execute("UPDATE storyboard_characters SET speaker = 'Narrator' WHERE speaker = 'narrator'")
