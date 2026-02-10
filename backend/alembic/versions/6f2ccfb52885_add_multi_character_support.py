"""add_multi_character_support

Revision ID: 6f2ccfb52885
Revises: 92320b5d62f9
Create Date: 2026-02-11 00:16:35.057609

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f2ccfb52885"
down_revision: Union[str, Sequence[str], None] = "92320b5d62f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add multi-character support fields to loras and scenes."""
    op.add_column(
        "loras",
        sa.Column("is_multi_character_capable", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "loras",
        sa.Column("multi_char_weight_scale", sa.Numeric(precision=3, scale=2), nullable=True),
    )
    op.add_column(
        "loras",
        sa.Column("multi_char_trigger_prompt", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "scenes",
        sa.Column("scene_mode", sa.String(length=10), server_default="single", nullable=False),
    )


def downgrade() -> None:
    """Remove multi-character support fields."""
    op.drop_column("scenes", "scene_mode")
    op.drop_column("loras", "multi_char_trigger_prompt")
    op.drop_column("loras", "multi_char_weight_scale")
    op.drop_column("loras", "is_multi_character_capable")
