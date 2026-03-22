"""add storyboard tone column and migrate confession to monologue

Revision ID: sp056a1b2c3d4
Revises: f7e8d9c0b1a2
Create Date: 2026-03-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "sp056a1b2c3d4"
down_revision: str = "f7e8d9c0b1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. tone 컬럼 추가
    op.add_column(
        "storyboards",
        sa.Column("tone", sa.String(30), server_default="intimate", nullable=False),
    )
    # 2. confession → monologue + emotional 데이터 마이그레이션
    op.execute("UPDATE storyboards SET structure = 'monologue', tone = 'emotional' WHERE structure = 'confession'")


def downgrade() -> None:
    # Best-effort: monologue+emotional 행을 confession으로 복원
    # 주의: upgrade() 이전부터 monologue+emotional이었던 행도 confession으로 변경될 수 있음
    op.execute("UPDATE storyboards SET structure = 'confession' WHERE structure = 'monologue' AND tone = 'emotional'")
    op.drop_column("storyboards", "tone")
