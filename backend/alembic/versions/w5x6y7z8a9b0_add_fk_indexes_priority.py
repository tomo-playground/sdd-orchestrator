"""Add FK indexes on 8 frequently-queried columns

Performance: FK 컬럼에 인덱스가 없으면 JOIN/DELETE 시 sequential scan 발생.
대상: scenes(2), groups(3), render_history(1), creative_sessions(1), style_profiles(1).

Revision ID: w5x6y7z8a9b0
Revises: v4w5x6y7z8a9
Create Date: 2026-02-28 18:00:00.000000
"""

from alembic import op

revision = "w5x6y7z8a9b0"
down_revision = "v4w5x6y7z8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_scenes_image_asset_id", "scenes", ["image_asset_id"])
    op.create_index("ix_scenes_environment_reference_id", "scenes", ["environment_reference_id"])
    op.create_index("ix_groups_render_preset_id", "groups", ["render_preset_id"])
    op.create_index("ix_groups_style_profile_id", "groups", ["style_profile_id"])
    op.create_index("ix_groups_narrator_voice_preset_id", "groups", ["narrator_voice_preset_id"])
    op.create_index("ix_render_history_media_asset_id", "render_history", ["media_asset_id"])
    op.create_index("ix_creative_sessions_character_id", "creative_sessions", ["character_id"])
    op.create_index("ix_style_profiles_sd_model_id", "style_profiles", ["sd_model_id"])


def downgrade() -> None:
    op.drop_index("ix_style_profiles_sd_model_id")
    op.drop_index("ix_creative_sessions_character_id")
    op.drop_index("ix_render_history_media_asset_id")
    op.drop_index("ix_groups_narrator_voice_preset_id")
    op.drop_index("ix_groups_style_profile_id")
    op.drop_index("ix_groups_render_preset_id")
    op.drop_index("ix_scenes_environment_reference_id")
    op.drop_index("ix_scenes_image_asset_id")
