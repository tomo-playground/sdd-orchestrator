"""Drop deprecated render_preset columns: narrator_voice, tts_engine, voice_design_prompt.

These are replaced by voice_preset_id FK which references voice_presets table
containing voice_design_prompt and voice_seed.

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-02-04
"""

from alembic import op
import sqlalchemy as sa

revision = "k5l6m7n8o9p0"
down_revision = "j4k5l6m7n8o9"
branch_labels = None
depends_on = None

_COLUMNS = ["narrator_voice", "tts_engine", "voice_design_prompt"]


def upgrade() -> None:
    # Drop check constraint on tts_engine first
    op.drop_constraint("ck_render_presets_tts_engine", "render_presets", type_="check")

    for col in _COLUMNS:
        op.drop_column("render_presets", col)


def downgrade() -> None:
    op.add_column("render_presets", sa.Column("voice_design_prompt", sa.Text(), nullable=True))
    op.add_column("render_presets", sa.Column("tts_engine", sa.String(20), nullable=True))
    op.add_column("render_presets", sa.Column("narrator_voice", sa.String(100), nullable=True))

    op.create_check_constraint(
        "ck_render_presets_tts_engine",
        "render_presets",
        "tts_engine IN ('qwen') OR tts_engine IS NULL",
    )
