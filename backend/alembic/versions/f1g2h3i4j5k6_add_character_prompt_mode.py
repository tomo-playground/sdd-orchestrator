"""add_character_prompt_mode

Revision ID: f1g2h3i4j5k6
Revises: 8adf3722a9ff
Create Date: 2026-01-25 15:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f1g2h3i4j5k6'
down_revision: str | Sequence[str] | None = '8adf3722a9ff'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add prompt_mode column to characters table.

    Values: 'auto' | 'standard' | 'lora'
    - auto: Detect mode based on LoRA presence
    - standard: No LoRA, full appearance tags
    - lora: With LoRA, scene-first ordering
    """
    op.add_column(
        'characters',
        sa.Column('prompt_mode', sa.String(length=20), nullable=False, server_default='auto')
    )


def downgrade() -> None:
    """Remove prompt_mode column from characters table."""
    op.drop_column('characters', 'prompt_mode')
