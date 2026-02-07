"""Add voice_presets table and render_presets.voice_preset_id

Revision ID: g1h2i3j4k5l6
Revises: e6f7a8b9c0d1
Create Date: 2026-02-02
"""
import sqlalchemy as sa

from alembic import op

revision = "g1h2i3j4k5l6"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {"t": table_name},
    )
    return result.fetchone() is not None


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table_name, "c": column_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    # 1. Create voice_presets table (skip if already created by create_all)
    if not _table_exists("voice_presets"):
        op.create_table(
            "voice_presets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
            sa.Column("source_type", sa.String(20), nullable=False),
            sa.Column("tts_engine", sa.String(20), nullable=True),
            sa.Column("audio_asset_id", sa.Integer(), sa.ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True),
            sa.Column("voice_design_prompt", sa.Text(), nullable=True),
            sa.Column("language", sa.String(20), nullable=False, server_default="korean"),
            sa.Column("sample_text", sa.Text(), nullable=True),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )

    # 2. CHECK constraints
    op.create_check_constraint(
        "ck_voice_presets_source_type",
        "voice_presets",
        "source_type IN ('generated', 'uploaded')",
    )
    op.create_check_constraint(
        "ck_voice_presets_tts_engine",
        "voice_presets",
        "tts_engine IN ('qwen') OR tts_engine IS NULL",
    )

    # 3. Partial unique indexes for name uniqueness per project
    op.create_index(
        "uq_voice_presets_project_name",
        "voice_presets",
        ["project_id", "name"],
        unique=True,
        postgresql_where=sa.text("project_id IS NOT NULL"),
    )
    op.create_index(
        "uq_voice_presets_system_name",
        "voice_presets",
        ["name"],
        unique=True,
        postgresql_where=sa.text("project_id IS NULL"),
    )

    # 4. Regular indexes
    op.create_index("ix_voice_presets_project_id", "voice_presets", ["project_id"])
    op.create_index("ix_voice_presets_audio_asset_id", "voice_presets", ["audio_asset_id"])

    # 5. Add voice_preset_id to render_presets
    if not _column_exists("render_presets", "voice_preset_id"):
        op.add_column(
            "render_presets",
            sa.Column("voice_preset_id", sa.Integer(), sa.ForeignKey("voice_presets.id", ondelete="SET NULL"), nullable=True),
        )
    op.create_index("ix_render_presets_voice_preset_id", "render_presets", ["voice_preset_id"], if_not_exists=True)

    # 6. Add missing index on render_presets.project_id (if not exists)
    op.create_index(
        "ix_render_presets_project_id",
        "render_presets",
        ["project_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_render_presets_project_id", "render_presets")
    op.drop_index("ix_render_presets_voice_preset_id", "render_presets")
    op.drop_column("render_presets", "voice_preset_id")
    op.drop_index("ix_voice_presets_audio_asset_id", "voice_presets")
    op.drop_index("ix_voice_presets_project_id", "voice_presets")
    op.drop_index("uq_voice_presets_system_name", "voice_presets")
    op.drop_index("uq_voice_presets_project_name", "voice_presets")
    op.drop_constraint("ck_voice_presets_tts_engine", "voice_presets", type_="check")
    op.drop_constraint("ck_voice_presets_source_type", "voice_presets", type_="check")
    op.drop_table("voice_presets")
