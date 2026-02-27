"""Normalize prompt_mode to 'auto' for all characters

prompt_mode 3-way 선택 제거에 따라 기존 'standard'/'lora' 값을 'auto'로 통일.
Auto가 이미 LoRA 유무로 런타임 결정하므로 동작 변화 없음.

Revision ID: u3v4w5x6y7z8
Revises: t2u3v4w5x6y7
Create Date: 2026-02-27 20:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "u3v4w5x6y7z8"
down_revision = "t2u3v4w5x6y7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE characters SET prompt_mode = 'auto' WHERE prompt_mode != 'auto'"))


def downgrade() -> None:
    # 원래 값 복원 불가 (data-only migration)
    pass
