"""Drop prompt_mode column from characters

prompt_mode 개념 제거. Auto가 이미 LoRA 유무로 런타임 결정하므로 컬럼 불필요.

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
    op.drop_column("characters", "prompt_mode")


def downgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("prompt_mode", sa.String(20), nullable=False, server_default="auto"),
    )
