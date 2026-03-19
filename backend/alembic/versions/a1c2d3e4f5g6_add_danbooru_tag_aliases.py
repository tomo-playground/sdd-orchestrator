"""add_danbooru_tag_aliases — 복합 포즈/표현/무효 태그 18건

Revision ID: a1c2d3e4f5g6
Revises: 1ccf182e0f06
Create Date: 2026-03-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c2d3e4f5g6"
down_revision: str | Sequence[str] | None = "1ccf182e0f06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (source_tag, target_tag, reason) — target_tag=None means "remove"
ALIASES: list[tuple[str, str | None, str]] = [
    # ── Compound pose split (9) ──
    ("standing_arms_crossed", "standing, crossed_arms", "Compound pose → Danbooru standard split"),
    ("standing_hands_on_hips", "standing, hands_on_hips", "Compound pose split"),
    ("standing_arms_up", "standing, arms_up", "Compound pose split"),
    ("standing_waving", "standing, waving", "Compound pose split"),
    ("standing_thumbs_up", "standing, thumbs_up", "Compound pose split"),
    ("standing_looking_up", "standing, looking_up", "Compound pose split"),
    ("standing_from_behind", "standing, from_behind", "Compound pose split"),
    ("sitting_chin_rest", "sitting, chin_rest", "Compound pose split"),
    ("sitting_leaning", "sitting, leaning_forward", "Compound pose split"),
    # ── Compound expression replace (4) ──
    ("happy_smile", "smile, happy", "Compound expression split"),
    ("sly_smile", "smirk", "Non-Danbooru → standard (33K posts)"),
    ("pensive_expression", "looking_down, closed_mouth", "Compound → visual equivalent"),
    ("puzzled_expression", "confused", "Non-Danbooru → standard (5K posts)"),
    # ── Invalid / deprecated tags (5) ──
    ("female", "1girl", "Non-Danbooru → SD standard"),
    ("male", "1boy", "Non-Danbooru → SD standard"),
    ("bishoujo", None, "Danbooru 0 posts, 1girl covers this"),
    ("daylight", "day, sunlight", "Danbooru 0 posts → valid combo"),
    ("extreme_close-up", "close-up, face_focus", "Danbooru 0 posts → valid combo"),
]


def upgrade() -> None:
    """Insert 18 Danbooru tag aliases."""
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
    """Remove the 18 aliases added in this migration."""
    connection = op.get_bind()
    sources = [a[0] for a in ALIASES]
    for source in sources:
        connection.execute(
            sa.text("DELETE FROM tag_aliases WHERE source_tag = :source"),
            {"source": source},
        )
