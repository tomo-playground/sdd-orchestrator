"""youtube_credentials restore project_id as required FK

Revision ID: d98cd7a8d450
Revises: 305de3fbe03d
Create Date: 2026-02-05 10:07:55.329928

"""

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from alembic import op

revision: str = "d98cd7a8d450"
down_revision: str | None = "305de3fbe03d"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Ensure project_id column exists with FK and unique constraint.

    The initial migration (305de3fbe03d) already created the table with
    project_id. This migration is a no-op if the schema is already correct,
    and restores the column if it was previously dropped.
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("youtube_credentials")}

    if "project_id" not in cols:
        op.add_column(
            "youtube_credentials",
            sa.Column("project_id", sa.Integer(), nullable=True),
        )

    # Ensure FK exists
    fks = {c["name"] for c in inspector.get_foreign_keys("youtube_credentials")}
    if "youtube_credentials_project_id_fkey" not in fks:
        op.create_foreign_key(
            "youtube_credentials_project_id_fkey",
            "youtube_credentials",
            "projects",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # Ensure unique constraint exists
    uqs = {c["name"] for c in inspector.get_unique_constraints("youtube_credentials")}
    if "youtube_credentials_project_id_key" not in uqs:
        op.create_unique_constraint(
            "youtube_credentials_project_id_key",
            "youtube_credentials",
            ["project_id"],
        )


def downgrade() -> None:
    """Drop project_id FK, unique, and column."""
    op.drop_constraint("youtube_credentials_project_id_key", "youtube_credentials", type_="unique")
    op.drop_constraint("youtube_credentials_project_id_fkey", "youtube_credentials", type_="foreignkey")
    op.drop_column("youtube_credentials", "project_id")
