"""Add soft delete (deleted_at) to storyboards, characters, prompt_histories.

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa

revision = "i3j4k5l6m7n8"
down_revision = "h2i3j4k5l6m7"
branch_labels = None
depends_on = None

_tables = ["storyboards", "characters", "prompt_histories"]


def upgrade() -> None:
    for table in _tables:
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(), nullable=True))
        op.create_index(f"ix_{table}_deleted_at", table, ["deleted_at"])


def downgrade() -> None:
    for table in _tables:
        op.drop_index(f"ix_{table}_deleted_at", table_name=table)
        op.drop_column(table, "deleted_at")
