"""remove task_type from creative_sessions

Revision ID: 1f854475bc89
Revises: a3b4c5d6e7f8
Create Date: 2026-02-08 10:52:03.459643

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1f854475bc89'
down_revision: str | Sequence[str] | None = 'a3b4c5d6e7f8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove task_type from creative_sessions (task type is now fixed to scenario)
    op.drop_index(op.f('ix_creative_sessions_task_type'), table_name='creative_sessions')
    op.drop_column('creative_sessions', 'task_type')


def downgrade() -> None:
    """Downgrade schema."""
    # Restore task_type column (default to 'scenario' for existing rows)
    op.add_column('creative_sessions', sa.Column('task_type', sa.VARCHAR(length=30), autoincrement=False, nullable=False, server_default='scenario'))
    op.create_index(op.f('ix_creative_sessions_task_type'), 'creative_sessions', ['task_type'], unique=False)
    # Remove server_default after backfill
    op.alter_column('creative_sessions', 'task_type', server_default=None)
