"""add youtube_credentials and render_history youtube columns

Revision ID: 305de3fbe03d
Revises: x8y9z0a1b2c3
Create Date: 2026-02-05 09:00:56.427026

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "305de3fbe03d"
down_revision: str | Sequence[str] | None = "x8y9z0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = inspector.get_table_names()

    # Create youtube_credentials table (skip if already created by create_all)
    if "youtube_credentials" not in existing_tables:
        op.create_table(
            "youtube_credentials",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("channel_id", sa.String(length=100), nullable=True),
            sa.Column("channel_title", sa.String(length=200), nullable=True),
            sa.Column("encrypted_token", sa.Text(), nullable=False),
            sa.Column("is_valid", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("project_id"),
        )

    # Add YouTube columns to render_history (skip if already exists)
    existing_columns = {c["name"] for c in inspector.get_columns("render_history")}
    if "youtube_video_id" not in existing_columns:
        op.add_column("render_history", sa.Column("youtube_video_id", sa.String(length=20), nullable=True))
    if "youtube_upload_status" not in existing_columns:
        op.add_column("render_history", sa.Column("youtube_upload_status", sa.String(length=20), nullable=True))
    if "youtube_uploaded_at" not in existing_columns:
        op.add_column("render_history", sa.Column("youtube_uploaded_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("render_history", "youtube_uploaded_at")
    op.drop_column("render_history", "youtube_upload_status")
    op.drop_column("render_history", "youtube_video_id")
    op.drop_table("youtube_credentials")
