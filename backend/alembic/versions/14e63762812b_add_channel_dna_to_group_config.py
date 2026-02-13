"""add_channel_dna_to_group_config

Revision ID: 14e63762812b
Revises: b5e6f7a8c9d0
Create Date: 2026-02-13 19:28:17.494692

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '14e63762812b'
down_revision: Union[str, Sequence[str], None] = 'b5e6f7a8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add channel_dna JSONB column to group_config."""
    op.add_column('group_config', sa.Column('channel_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Remove channel_dna column from group_config."""
    op.drop_column('group_config', 'channel_dna')
