"""Rename character preview_image → reference_image fields.

preview_image_asset_id → reference_image_asset_id
FK constraint + index updated accordingly.

Revision ID: 7d60fb618f36
Revises: 91b22bb4289f
Create Date: 2026-03-07
"""

from alembic import op

revision = "7d60fb618f36"
down_revision = "91b22bb4289f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Rename column
    op.alter_column("characters", "preview_image_asset_id", new_column_name="reference_image_asset_id")

    # 2. Replace FK constraint (PostgreSQL has no ALTER CONSTRAINT RENAME)
    op.drop_constraint("fk_characters_preview_image_asset_id", "characters", type_="foreignkey")
    op.create_foreign_key(
        "fk_characters_reference_image_asset_id",
        "characters",
        "media_assets",
        ["reference_image_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3. Add FK index (was missing — DBA recommendation)
    op.create_index("ix_characters_reference_image_asset_id", "characters", ["reference_image_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_characters_reference_image_asset_id", table_name="characters")

    op.drop_constraint("fk_characters_reference_image_asset_id", "characters", type_="foreignkey")
    op.create_foreign_key(
        "fk_characters_preview_image_asset_id",
        "characters",
        "media_assets",
        ["preview_image_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column("characters", "reference_image_asset_id", new_column_name="preview_image_asset_id")
