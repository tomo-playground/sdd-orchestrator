"""Add TTS columns to render_presets

Revision ID: e6f7a8b9c0d1
Revises: d2e3f4a5b6c7
Create Date: 2026-02-02
"""
from alembic import op
import sqlalchemy as sa

revision = "e6f7a8b9c0d1"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("render_presets", sa.Column("tts_engine", sa.String(20), nullable=True))
    op.add_column("render_presets", sa.Column("voice_design_prompt", sa.Text(), nullable=True))
    op.add_column("render_presets", sa.Column("voice_ref_audio_url", sa.Text(), nullable=True))

    op.create_check_constraint(
        "ck_render_presets_tts_engine",
        "render_presets",
        "tts_engine IN ('qwen') OR tts_engine IS NULL",
    )

    # Set system presets to use qwen
    op.execute("UPDATE render_presets SET tts_engine = 'qwen' WHERE is_system = true")


def downgrade() -> None:
    op.drop_constraint("ck_render_presets_tts_engine", "render_presets", type_="check")
    op.drop_column("render_presets", "voice_ref_audio_url")
    op.drop_column("render_presets", "voice_design_prompt")
    op.drop_column("render_presets", "tts_engine")
