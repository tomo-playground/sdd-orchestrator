"""add reference_env_tags and reference_camera_tags to style_profiles

Revision ID: 876d46988906
Revises: 5bdd12ca852c
Create Date: 2026-02-28 20:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "876d46988906"
down_revision: str | Sequence[str] | None = "5bdd12ca852c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Current config_prompt.py defaults — seed into existing rows
_DEFAULT_ENV_TAGS = [
    "(white_background:1.8)",
    "(simple_background:1.5)",
    "plain_background",
    "solid_background",
    "no_shadow",
]
_DEFAULT_CAMERA_TAGS = [
    "(solo:1.5)",
    "full_body",
    "(standing:1.2)",
    "looking_at_viewer",
    "facing_viewer",
]


def upgrade() -> None:
    """Add JSONB columns and seed existing profiles."""
    op.add_column("style_profiles", sa.Column("reference_env_tags", JSONB(), nullable=True))
    op.add_column("style_profiles", sa.Column("reference_camera_tags", JSONB(), nullable=True))

    # Seed existing rows with current defaults
    style_profiles = sa.table(
        "style_profiles",
        sa.column("reference_env_tags", JSONB),
        sa.column("reference_camera_tags", JSONB),
    )
    op.execute(
        style_profiles.update().values(
            reference_env_tags=_DEFAULT_ENV_TAGS,
            reference_camera_tags=_DEFAULT_CAMERA_TAGS,
        )
    )


def downgrade() -> None:
    """Remove JSONB columns."""
    op.drop_column("style_profiles", "reference_camera_tags")
    op.drop_column("style_profiles", "reference_env_tags")
