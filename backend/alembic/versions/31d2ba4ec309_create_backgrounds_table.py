"""create_backgrounds_table

Revision ID: 31d2ba4ec309
Revises: 6f2ccfb52885
Create Date: 2026-02-11 19:12:55.981155

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '31d2ba4ec309'
down_revision: str | Sequence[str] | None = '6f2ccfb52885'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('backgrounds',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('image_asset_id', sa.Integer(), nullable=True),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.Column('weight', sa.Float(), nullable=False),
    sa.Column('is_system', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['image_asset_id'], ['media_assets.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backgrounds_category'), 'backgrounds', ['category'], unique=False)
    op.create_index(op.f('ix_backgrounds_deleted_at'), 'backgrounds', ['deleted_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_backgrounds_deleted_at'), table_name='backgrounds')
    op.drop_index(op.f('ix_backgrounds_category'), table_name='backgrounds')
    op.drop_table('backgrounds')
