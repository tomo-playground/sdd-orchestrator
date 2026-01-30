"""add_tag_deprecation_fields

Revision ID: 59c63582ece4
Revises: d4fc742b4bca
Create Date: 2026-01-31 01:40:25.790723

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59c63582ece4'
down_revision: Union[str, Sequence[str], None] = 'd4fc742b4bca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deprecation and replacement fields to tags table."""
    # Add is_active column (default True for existing tags)
    op.add_column('tags', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.create_index('ix_tags_is_active', 'tags', ['is_active'])

    # Add deprecated_reason column
    op.add_column('tags', sa.Column('deprecated_reason', sa.String(200), nullable=True))

    # Add replacement_tag_id column (foreign key to tags.id)
    op.add_column('tags', sa.Column('replacement_tag_id', sa.Integer(), nullable=True))

    # Deprecate known non-Danbooru tags
    op.execute("""
        UPDATE tags
        SET is_active = false,
            deprecated_reason = 'Not in Danbooru dataset (0 posts)'
        WHERE name IN ('room', 'interior')
    """)

    # Set replacement for 'room' -> 'indoors'
    op.execute("""
        UPDATE tags
        SET replacement_tag_id = (SELECT id FROM tags WHERE name = 'indoors' LIMIT 1)
        WHERE name = 'room'
    """)

    # Set replacement for 'interior' -> 'indoors'
    op.execute("""
        UPDATE tags
        SET replacement_tag_id = (SELECT id FROM tags WHERE name = 'indoors' LIMIT 1)
        WHERE name = 'interior'
    """)


def downgrade() -> None:
    """Remove deprecation fields from tags table."""
    op.drop_index('ix_tags_is_active', 'tags')
    op.drop_column('tags', 'replacement_tag_id')
    op.drop_column('tags', 'deprecated_reason')
    op.drop_column('tags', 'is_active')
