"""rename active to is_active

Revision ID: 22e99aa5ecbd
Revises: 4c37698107e5
Create Date: 2026-02-10

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '22e99aa5ecbd'
down_revision: Union[str, Sequence[str], None] = '4c37698107e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that have 'active' column to rename to 'is_active'
TABLES = ['tag_rules', 'tag_aliases', 'tag_filters', 'classification_rules']


def upgrade() -> None:
    """Rename 'active' to 'is_active' in tag system tables for naming consistency."""
    for table in TABLES:
        op.alter_column(table, 'active', new_column_name='is_active')


def downgrade() -> None:
    """Revert 'is_active' back to 'active'."""
    for table in TABLES:
        op.alter_column(table, 'is_active', new_column_name='active')
