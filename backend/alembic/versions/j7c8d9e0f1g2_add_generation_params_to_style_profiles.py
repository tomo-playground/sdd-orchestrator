"""Add generation params to style_profiles

StyleProfile별 최적 생성 파라미터 자동 적용을 위해
style_profiles 테이블에 default_steps, default_cfg_scale,
default_sampler_name, default_clip_skip 컬럼 추가.

- Realistic(id=2) → steps=6, cfg_scale=1.5, sampler="DPM++ SDE Karras", clip_skip=1
- Default Anime(id=1) → steps=28, cfg_scale=7.0, sampler="DPM++ 2M Karras", clip_skip=2
- 나머지 → NULL (전역 기본값 사용)

Revision ID: j7c8d9e0f1g2
Revises: i6b7c8d9e0f1
Create Date: 2026-02-21 22:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "j7c8d9e0f1g2"
down_revision = "i6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("style_profiles", sa.Column("default_steps", sa.Integer(), nullable=True))
    op.add_column("style_profiles", sa.Column("default_cfg_scale", sa.Float(), nullable=True))
    op.add_column("style_profiles", sa.Column("default_sampler_name", sa.String(50), nullable=True))
    op.add_column("style_profiles", sa.Column("default_clip_skip", sa.Integer(), nullable=True))

    # Data migration
    op.execute(
        "UPDATE style_profiles SET default_steps = 28, default_cfg_scale = 7.0, "
        "default_sampler_name = 'DPM++ 2M Karras', default_clip_skip = 2 WHERE id = 1"
    )
    op.execute(
        "UPDATE style_profiles SET default_steps = 6, default_cfg_scale = 1.5, "
        "default_sampler_name = 'DPM++ SDE Karras', default_clip_skip = 1 WHERE id = 2"
    )


def downgrade() -> None:
    op.drop_column("style_profiles", "default_clip_skip")
    op.drop_column("style_profiles", "default_sampler_name")
    op.drop_column("style_profiles", "default_cfg_scale")
    op.drop_column("style_profiles", "default_steps")
