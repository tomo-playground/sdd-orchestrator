"""add_restricted_tags_to_tag_filters

Revision ID: 3befa9fd7c2e
Revises: b7ab5851ca30
Create Date: 2026-02-01 15:52:25.669832

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3befa9fd7c2e"
down_revision: str | Sequence[str] | None = "b7ab5851ca30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add restricted tags to tag_filters table (SSOT migration from v3_composition.py)."""
    # List of tags that should not appear in Character Identity DNA (was hardcoded)
    restricted_tags = [
        "background",
        "kitchen",
        "room",
        "outdoors",
        "indoors",
        "scenery",
        "nature",
        "mountain",
        "street",
        "office",
        "bedroom",
        "bathroom",
        "garden",
    ]

    # Insert restricted tags into tag_filters
    for tag in restricted_tags:
        op.execute(
            f"""
            INSERT INTO tag_filters (tag_name, filter_type, reason, active, created_at, updated_at)
            VALUES (
                '{tag}',
                'restricted',
                'Background/situation tag - should not be in Character Identity DNA',
                true,
                NOW(),
                NOW()
            )
            ON CONFLICT (tag_name) DO NOTHING;
            """
        )


def downgrade() -> None:
    """Remove restricted tags added in this migration."""
    restricted_tags = [
        "background",
        "kitchen",
        "room",
        "outdoors",
        "indoors",
        "scenery",
        "nature",
        "mountain",
        "street",
        "office",
        "bedroom",
        "bathroom",
        "garden",
    ]

    for tag in restricted_tags:
        op.execute(
            f"""
            DELETE FROM tag_filters
            WHERE tag_name = '{tag}' AND filter_type = 'restricted';
            """
        )
