"""add_group_deleted_at

Revision ID: e0432dd57121
Revises: 08670f62151d
Create Date: 2026-03-13 23:54:09.513535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0432dd57121'
down_revision: Union[str, Sequence[str], None] = '08670f62151d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deleted_at column to groups table for soft delete support."""
    op.add_column('groups', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_groups_deleted_at'), 'groups', ['deleted_at'], unique=False)


def downgrade() -> None:
    """Remove deleted_at column from groups table."""
    op.drop_index(op.f('ix_groups_deleted_at'), table_name='groups')
    op.drop_column('groups', 'deleted_at')
