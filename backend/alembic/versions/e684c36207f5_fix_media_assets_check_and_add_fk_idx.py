"""fix media_assets CHECK constraint and add storyboard_characters FK index

#54: Expand ck_media_assets_file_type to include 'cache' and 'candidate'
     so ORM model and DB CHECK are consistent.
#56: Add btree index on storyboard_characters.character_id (FK index policy).

Revision ID: e684c36207f5
Revises: a4b5c6d7e8f9
Create Date: 2026-02-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e684c36207f5"
down_revision: str | Sequence[str] | None = "a4b5c6d7e8f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # #54: Replace narrow CHECK with expanded one
    op.drop_constraint("ck_media_assets_file_type", "media_assets", type_="check")
    op.create_check_constraint(
        "ck_media_assets_file_type",
        "media_assets",
        "file_type IN ('image', 'audio', 'video', 'cache', 'candidate')",
    )

    # #56: Add missing FK index on storyboard_characters.character_id
    op.create_index(
        "ix_storyboard_characters_character_id",
        "storyboard_characters",
        ["character_id"],
    )


def downgrade() -> None:
    # Reverse #56
    op.drop_index("ix_storyboard_characters_character_id", table_name="storyboard_characters")

    # Reverse #54: Restore original narrow CHECK
    op.drop_constraint("ck_media_assets_file_type", "media_assets", type_="check")
    op.create_check_constraint(
        "ck_media_assets_file_type",
        "media_assets",
        "file_type IN ('image', 'audio', 'video')",
    )
