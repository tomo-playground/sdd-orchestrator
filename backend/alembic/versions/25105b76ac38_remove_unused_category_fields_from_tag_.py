"""Remove unused category fields from tag_rules

Revision ID: 25105b76ac38
Revises: a7be23c70433
Create Date: 2026-01-30 13:14:19.304659

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "25105b76ac38"
down_revision: str | Sequence[str] | None = "a7be23c70433"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove unused category-level conflict fields from tag_rules.

    Removed fields (0 usage, all 16 rules use tag-level only):
    - source_category: Category-level conflict source (never used)
    - target_category: Category-level conflict target (never used)

    All existing rules use source_tag_id/target_tag_id for tag-level conflicts.
    """
    # Drop indexes first if they exist
    op.drop_index("ix_tag_rules_source_category", table_name="tag_rules", if_exists=True)
    op.drop_index("ix_tag_rules_target_category", table_name="tag_rules", if_exists=True)

    # Remove unused columns
    op.drop_column("tag_rules", "source_category")
    op.drop_column("tag_rules", "target_category")


def downgrade() -> None:
    """Restore category-level fields (as unused/empty)."""
    # Re-add columns
    op.add_column("tag_rules", sa.Column("source_category", sa.String(50), nullable=True))
    op.add_column("tag_rules", sa.Column("target_category", sa.String(50), nullable=True))

    # Re-create indexes
    op.create_index("ix_tag_rules_source_category", "tag_rules", ["source_category"])
    op.create_index("ix_tag_rules_target_category", "tag_rules", ["target_category"])
