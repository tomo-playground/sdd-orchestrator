"""Migrate bgm_mode from file/ai to manual/auto.

Revision ID: d1a2b3c4e5f6
Revises: cb482830a656
Create Date: 2026-02-20
"""

from alembic import op

revision = "d1a2b3c4e5f6"
down_revision = "cb482830a656"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Migrate bgm_mode: file/ai → manual, update CHECK constraint."""
    # 1. Drop old CHECK constraint
    op.drop_constraint("ck_render_presets_bgm_mode", "render_presets", type_="check")

    # 2. Data migration: file/ai → manual
    op.execute("UPDATE render_presets SET bgm_mode = 'manual' WHERE bgm_mode IN ('file', 'ai')")

    # 3. New CHECK constraint
    op.create_check_constraint(
        "ck_render_presets_bgm_mode",
        "render_presets",
        "bgm_mode IN ('manual', 'auto')",
    )


def downgrade() -> None:
    """Revert bgm_mode: manual → file, restore old CHECK constraint."""
    op.drop_constraint("ck_render_presets_bgm_mode", "render_presets", type_="check")

    # Revert data: manual → file (best-effort; can't distinguish original file vs ai)
    op.execute("UPDATE render_presets SET bgm_mode = 'file' WHERE bgm_mode = 'manual'")

    op.create_check_constraint(
        "ck_render_presets_bgm_mode",
        "render_presets",
        "bgm_mode IN ('file', 'ai')",
    )
