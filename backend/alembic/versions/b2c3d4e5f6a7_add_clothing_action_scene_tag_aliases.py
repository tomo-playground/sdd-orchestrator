"""add_clothing_action_scene_tag_aliases — 의류/동작/씬 태그 5건

Revision ID: b2c3d4e5f6a7
Revises: 94a5878b5de6
Create Date: 2026-03-15 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "94a5878b5de6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (source_tag, target_tag, reason)
ALIASES: list[tuple[str, str, str]] = [
    ("navy_necktie", "blue_necktie", "Color prefix non-standard → Danbooru blue_necktie"),
    ("black_slacks", "black_pants", "Non-Danbooru clothing tag → standard black_pants"),
    ("arms_crossed", "crossed_arms", "Word order → Danbooru standard crossed_arms (200K+ posts)"),
    ("daytime", "day", "Non-Danbooru lighting tag → standard day"),
    ("clutching_bag", "holding_bag", "Non-Danbooru action tag → standard holding_bag"),
]


def upgrade() -> None:
    """Insert 5 clothing/action/scene tag aliases."""
    connection = op.get_bind()
    for source, target, reason in ALIASES:
        connection.execute(
            sa.text(
                "INSERT INTO tag_aliases (source_tag, target_tag, reason, is_active) "
                "SELECT :source, :target, :reason, true "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM tag_aliases WHERE source_tag = :source"
                ")"
            ),
            {"source": source, "target": target, "reason": reason},
        )


def downgrade() -> None:
    """Remove the 5 aliases added in this migration."""
    connection = op.get_bind()
    sources = [a[0] for a in ALIASES]
    for source in sources:
        connection.execute(
            sa.text("DELETE FROM tag_aliases WHERE source_tag = :source"),
            {"source": source},
        )
