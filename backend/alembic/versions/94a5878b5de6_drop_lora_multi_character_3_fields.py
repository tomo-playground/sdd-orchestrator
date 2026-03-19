"""drop lora multi-character 3 fields

Revision ID: 94a5878b5de6
Revises: c802651d6ede
Create Date: 2026-03-14 20:51:34.334541

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "94a5878b5de6"
down_revision: str | Sequence[str] | None = "c802651d6ede"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Phase 30-O: LoRA multi-character 3필드 제거 (V-Pred에서 불필요)."""
    op.drop_column("loras", "is_multi_character_capable")
    op.drop_column("loras", "multi_char_weight_scale")
    op.drop_column("loras", "multi_char_trigger_prompt")


def downgrade() -> None:
    """Restore LoRA multi-character 3 fields."""
    op.add_column(
        "loras",
        sa.Column(
            "is_multi_character_capable",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "loras",
        sa.Column(
            "multi_char_weight_scale",
            sa.NUMERIC(precision=3, scale=2),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "loras",
        sa.Column(
            "multi_char_trigger_prompt",
            sa.VARCHAR(length=200),
            autoincrement=False,
            nullable=True,
        ),
    )
