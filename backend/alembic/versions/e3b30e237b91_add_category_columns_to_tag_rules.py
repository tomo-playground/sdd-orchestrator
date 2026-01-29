"""add_category_columns_to_tag_rules

Revision ID: e3b30e237b91
Revises: 5d52713e8a1f
Create Date: 2026-01-29 19:09:49.827440

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3b30e237b91'
down_revision: Union[str, Sequence[str], None] = '5d52713e8a1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add category columns to tag_rules and make tag IDs nullable."""
    # Add new category columns
    op.add_column('tag_rules', sa.Column('source_category', sa.String(length=50), nullable=True))
    op.add_column('tag_rules', sa.Column('target_category', sa.String(length=50), nullable=True))
    
    # Create indexes for category columns
    op.create_index('idx_tag_rules_source_category', 'tag_rules', ['source_category'])
    op.create_index('idx_tag_rules_target_category', 'tag_rules', ['target_category'])
    
    # Make tag ID columns nullable (they were NOT NULL before)
    op.alter_column('tag_rules', 'source_tag_id', nullable=True)
    op.alter_column('tag_rules', 'target_tag_id', nullable=True)


def downgrade() -> None:
    """Remove category columns and restore tag IDs to NOT NULL."""
    # Drop indexes
    op.drop_index('idx_tag_rules_target_category', table_name='tag_rules')
    op.drop_index('idx_tag_rules_source_category', table_name='tag_rules')
    
    # Remove category columns
    op.drop_column('tag_rules', 'target_category')
    op.drop_column('tag_rules', 'source_category')
    
    # Restore tag IDs to NOT NULL (only if no NULL values exist)
    op.alter_column('tag_rules', 'source_tag_id', nullable=False)
    op.alter_column('tag_rules', 'target_tag_id', nullable=False)
