"""Clear white_background reference_env_tags from style_profiles

Revision ID: f7e8d9c0b1a2
Revises: z8a9b0c1d2e3
Create Date: 2026-03-17

Experiment proved: scene-concept references (no forced white background)
produce far better character consistency via IP-Adapter transfer.
Clearing env_tags lets SD generate natural backgrounds from style LoRA.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "f7e8d9c0b1a2"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Restore values for rollback
_PREV_ENV_TAGS_BY_NAME = {
    "Flat Color Anime": ["(white_background:1.5)", "(simple_background:1.3)"],
    "Romantic Warm Anime": [
        "(white_background:1.8)",
        "(simple_background:1.5)",
        "plain_background",
        "solid_background",
        "no_shadow",
    ],
}


def upgrade() -> None:
    """Clear reference_env_tags to remove white background forcing."""
    style_profiles = sa.table(
        "style_profiles",
        sa.column("reference_env_tags", JSONB),
    )
    op.execute(style_profiles.update().values(reference_env_tags=[]))


def downgrade() -> None:
    """Restore original white background env tags per profile."""
    conn = op.get_bind()
    style_profiles = sa.table(
        "style_profiles",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("reference_env_tags", JSONB),
    )
    for name, tags in _PREV_ENV_TAGS_BY_NAME.items():
        conn.execute(style_profiles.update().where(style_profiles.c.name == name).values(reference_env_tags=tags))
