"""character_multi_lora_support

Revision ID: 66645c47c203
Revises: b6091b17d9b3
Create Date: 2026-01-24 15:08:30.014445

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '66645c47c203'
down_revision: str | Sequence[str] | None = 'b6091b17d9b3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add multi-LoRA support to characters."""
    # Add new columns
    op.add_column('characters', sa.Column('description', sa.String(500), nullable=True))
    op.add_column('characters', sa.Column('loras', JSONB, nullable=True))

    # Migrate existing lora_id/lora_weight to loras array
    op.execute("""
        UPDATE characters
        SET loras = jsonb_build_array(
            jsonb_build_object('lora_id', lora_id, 'weight', lora_weight)
        )
        WHERE lora_id IS NOT NULL
    """)

    # Drop old columns and constraint
    op.drop_constraint('characters_lora_id_fkey', 'characters', type_='foreignkey')
    op.drop_column('characters', 'lora_id')
    op.drop_column('characters', 'lora_weight')


def downgrade() -> None:
    """Revert to single LoRA per character."""
    # Add back old columns
    op.add_column('characters', sa.Column('lora_id', sa.Integer, nullable=True))
    op.add_column('characters', sa.Column('lora_weight', sa.Numeric(3, 2), nullable=True))

    # Migrate first LoRA from array back to single columns
    op.execute("""
        UPDATE characters
        SET lora_id = (loras->0->>'lora_id')::integer,
            lora_weight = (loras->0->>'weight')::numeric
        WHERE loras IS NOT NULL AND jsonb_array_length(loras) > 0
    """)

    # Add back foreign key
    op.create_foreign_key('characters_lora_id_fkey', 'characters', 'loras', ['lora_id'], ['id'])

    # Drop new columns
    op.drop_column('characters', 'loras')
    op.drop_column('characters', 'description')
