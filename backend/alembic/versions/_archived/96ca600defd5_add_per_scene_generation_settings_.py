"""add per-scene generation settings override

Revision ID: 96ca600defd5
Revises: 2f2117268a07
Create Date: 2026-02-06 21:19:48.406562

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '96ca600defd5'
down_revision: str | Sequence[str] | None = '2f2117268a07'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add per-scene generation settings override columns."""
    op.add_column('scenes', sa.Column('use_controlnet', sa.Boolean(), nullable=True))
    op.add_column('scenes', sa.Column('controlnet_weight', sa.Float(), nullable=True))
    op.add_column('scenes', sa.Column('use_ip_adapter', sa.Boolean(), nullable=True))
    op.add_column('scenes', sa.Column('ip_adapter_reference', sa.String(length=255), nullable=True))
    op.add_column('scenes', sa.Column('ip_adapter_weight', sa.Float(), nullable=True))
    op.add_column('scenes', sa.Column('multi_gen_enabled', sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Remove per-scene generation settings override columns."""
    op.drop_column('scenes', 'multi_gen_enabled')
    op.drop_column('scenes', 'ip_adapter_weight')
    op.drop_column('scenes', 'ip_adapter_reference')
    op.drop_column('scenes', 'use_ip_adapter')
    op.drop_column('scenes', 'controlnet_weight')
    op.drop_column('scenes', 'use_controlnet')
