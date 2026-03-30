"""SP-117: v-pred → epsilon checkpoint transition

Revision ID: sp117_epsilon
Revises: 1c11eaba13d6
Create Date: 2026-03-29

- INSERT NoobAI-XL Epsilon 1.1 into sd_models
- Deactivate v-pred checkpoint (is_active=False)
- Update StyleProfile id=3 to use epsilon model + CFG 7.0
"""

revision = "sp117_epsilon"
down_revision = "1c11eaba13d6"
branch_labels = None
depends_on = None

import sqlalchemy as sa

from alembic import op


def upgrade() -> None:
    # 1. Insert epsilon checkpoint
    op.execute(
        sa.text(
            """
            INSERT INTO sd_models (name, display_name, model_type, base_model, is_active)
            VALUES (
                'noobaiXL_epsPred11.safetensors',
                'NoobAI-XL Epsilon 1.1',
                'checkpoint',
                'SDXL',
                true
            )
            ON CONFLICT (name) DO UPDATE SET is_active = true
            """
        )
    )

    # 2. Deactivate v-pred checkpoint
    op.execute(
        sa.text(
            """
            UPDATE sd_models
            SET is_active = false
            WHERE name = 'noobaiXLNAIXL_vPred10Version.safetensors'
            """
        )
    )

    # 3. Update StyleProfile id=3 (유일한 active 프로필) to use epsilon model + CFG 7.0
    # NOTE: 다른 프로필(id=2,5,7,10)은 is_active=false 비활성 상태 — 전환 불필요
    op.execute(
        sa.text(
            """
            UPDATE style_profiles
            SET sd_model_id = (
                    SELECT id FROM sd_models
                    WHERE name = 'noobaiXL_epsPred11.safetensors'
                ),
                default_cfg_scale = 7.0
            WHERE id = 3
            """
        )
    )


def downgrade() -> None:
    # Restore StyleProfile to v-pred
    op.execute(
        sa.text(
            """
            UPDATE style_profiles
            SET sd_model_id = (
                    SELECT id FROM sd_models
                    WHERE name = 'noobaiXLNAIXL_vPred10Version.safetensors'
                ),
                default_cfg_scale = 4.5
            WHERE id = 3
            """
        )
    )

    # Re-activate v-pred
    op.execute(
        sa.text(
            """
            UPDATE sd_models
            SET is_active = true
            WHERE name = 'noobaiXLNAIXL_vPred10Version.safetensors'
            """
        )
    )

    # Remove epsilon checkpoint
    op.execute(
        sa.text(
            """
            DELETE FROM sd_models
            WHERE name = 'noobaiXL_epsPred11.safetensors'
            """
        )
    )
