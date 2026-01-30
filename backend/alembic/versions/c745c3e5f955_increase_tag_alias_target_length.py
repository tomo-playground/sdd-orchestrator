"""increase_tag_alias_target_length

Revision ID: c745c3e5f955
Revises: e3b30e237b91
Create Date: 2026-01-29 21:39:12.181693

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c745c3e5f955'
down_revision: str | Sequence[str] | None = 'e3b30e237b91'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('tag_aliases', 'target_tag',
               existing_type=sa.VARCHAR(length=100),
               type_=sa.String(length=500),
               existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('tag_aliases', 'target_tag',
               existing_type=sa.String(length=500),
               type_=sa.VARCHAR(length=100),
               existing_nullable=True)
