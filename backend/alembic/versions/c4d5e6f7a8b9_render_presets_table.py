"""Create render_presets table and migrate groups default_* columns

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-02-02 20:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: str | Sequence[str] | None = 'b3c4d5e6f7a8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create render_presets table (IF NOT EXISTS for idempotency —
    #    Base.metadata.create_all() may have already created the table)
    conn = op.get_bind()
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS render_presets (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            is_system BOOLEAN NOT NULL DEFAULT true,
            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            narrator_voice VARCHAR(100),
            bgm_file VARCHAR(255),
            bgm_volume FLOAT,
            audio_ducking BOOLEAN,
            scene_text_font VARCHAR(255),
            layout_style VARCHAR(50),
            frame_style VARCHAR(255),
            transition_type VARCHAR(50),
            ken_burns_preset VARCHAR(50),
            ken_burns_intensity FLOAT,
            speed_multiplier FLOAT,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        )
    """))

    # 2. Seed 3 system presets (skip if already seeded)
    existing = conn.execute(text("SELECT count(*) FROM render_presets")).scalar()
    if existing == 0:
        conn.execute(text("""
            INSERT INTO render_presets (name, description, is_system, narrator_voice, bgm_file, bgm_volume, audio_ducking, scene_text_font, layout_style, frame_style, transition_type, ken_burns_preset, ken_burns_intensity, speed_multiplier)
            VALUES
            ('Post 표준', 'Post 레이아웃, overlay_minimal, random BGM/transition, speed 1.3', true, 'ko-KR-SunHiNeural', 'random', 0.25, true, '온글잎 박다현체.ttf', 'post', 'overlay_minimal.png', 'random', 'random', 1.0, 1.3),
            ('Full 시네마틱', 'Full 레이아웃, no frame, fade transition, random BGM, speed 1.0', true, 'ko-KR-SunHiNeural', 'random', 0.15, true, '온글잎 박다현체.ttf', 'full', NULL, 'fade', 'random', 1.0, 1.0),
            ('빠른 초안', 'Post 레이아웃, no BGM, no transition, no Ken Burns, speed 1.0', true, 'ko-KR-SunHiNeural', NULL, 0.0, false, '온글잎 박다현체.ttf', 'post', NULL, 'none', 'none', 1.0, 1.0)
        """))

    # 3. Add render_preset_id FK to groups
    op.add_column('groups', sa.Column('render_preset_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_groups_render_preset_id',
        'groups', 'render_presets',
        ['render_preset_id'], ['id'],
        ondelete='SET NULL',
    )

    # 4. Best-effort: map existing groups to presets based on layout_style
    conn.execute(text("""
        UPDATE groups SET render_preset_id = (
            SELECT id FROM render_presets WHERE name = 'Post 표준' LIMIT 1
        )
        WHERE default_layout_style = 'post' OR default_layout_style IS NULL
    """))
    conn.execute(text("""
        UPDATE groups SET render_preset_id = (
            SELECT id FROM render_presets WHERE name = 'Full 시네마틱' LIMIT 1
        )
        WHERE default_layout_style = 'full' AND render_preset_id IS NULL
    """))

    # 5. Drop old default_* columns
    op.drop_column('groups', 'default_narrator_voice')
    op.drop_column('groups', 'default_bgm_file')
    op.drop_column('groups', 'default_bgm_volume')
    op.drop_column('groups', 'default_audio_ducking')
    op.drop_column('groups', 'default_scene_text_font')
    op.drop_column('groups', 'default_layout_style')
    op.drop_column('groups', 'default_frame_style')
    op.drop_column('groups', 'default_transition_type')
    op.drop_column('groups', 'default_ken_burns_preset')
    op.drop_column('groups', 'default_ken_burns_intensity')
    op.drop_column('groups', 'default_speed_multiplier')


def downgrade() -> None:
    # 1. Re-add default_* columns
    op.add_column('groups', sa.Column('default_narrator_voice', sa.String(100), nullable=True))
    op.add_column('groups', sa.Column('default_bgm_file', sa.String(255), nullable=True))
    op.add_column('groups', sa.Column('default_bgm_volume', sa.Float(), nullable=True))
    op.add_column('groups', sa.Column('default_audio_ducking', sa.Boolean(), nullable=True))
    op.add_column('groups', sa.Column('default_scene_text_font', sa.String(255), nullable=True))
    op.add_column('groups', sa.Column('default_layout_style', sa.String(50), nullable=True))
    op.add_column('groups', sa.Column('default_frame_style', sa.String(255), nullable=True))
    op.add_column('groups', sa.Column('default_transition_type', sa.String(50), nullable=True))
    op.add_column('groups', sa.Column('default_ken_burns_preset', sa.String(50), nullable=True))
    op.add_column('groups', sa.Column('default_ken_burns_intensity', sa.Float(), nullable=True))
    op.add_column('groups', sa.Column('default_speed_multiplier', sa.Float(), nullable=True))

    # 2. Restore data from presets
    conn = op.get_bind()
    conn.execute(text("""
        UPDATE groups SET
            default_narrator_voice = rp.narrator_voice,
            default_bgm_file = rp.bgm_file,
            default_bgm_volume = rp.bgm_volume,
            default_audio_ducking = rp.audio_ducking,
            default_scene_text_font = rp.scene_text_font,
            default_layout_style = rp.layout_style,
            default_frame_style = rp.frame_style,
            default_transition_type = rp.transition_type,
            default_ken_burns_preset = rp.ken_burns_preset,
            default_ken_burns_intensity = rp.ken_burns_intensity,
            default_speed_multiplier = rp.speed_multiplier
        FROM render_presets rp
        WHERE groups.render_preset_id = rp.id
    """))

    # 3. Drop FK and column
    op.drop_constraint('fk_groups_render_preset_id', 'groups', type_='foreignkey')
    op.drop_column('groups', 'render_preset_id')

    # 4. Drop render_presets table
    op.drop_table('render_presets')
