"""Add avatar_key to projects

Revision ID: c1d2e3f4a5b6
Revises: d5e6f7a8b9c0
Create Date: 2026-02-02 23:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: str = 'd5e6f7a8b9c0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('avatar_key', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'avatar_key')
