"""Add default_enable_hr to style_profiles

StyleProfile별 Hi-Res(Hires Fix) 기본값 자동 적용을 위해
style_profiles 테이블에 default_enable_hr 컬럼 추가.

- Realistic(id=2) → True (512→768 업스케일 필수)
- Default Anime(id=1) → False (512px 충분)
- 나머지 → NULL (전역 기본값 사용, 즉 OFF)

Revision ID: k8d9e0f1g2h3
Revises: j7c8d9e0f1g2
Create Date: 2026-02-21 23:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "k8d9e0f1g2h3"
down_revision = "j7c8d9e0f1g2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("style_profiles", sa.Column("default_enable_hr", sa.Boolean(), nullable=True))

    # Data migration
    op.execute("UPDATE style_profiles SET default_enable_hr = true WHERE id = 2")
    op.execute("UPDATE style_profiles SET default_enable_hr = false WHERE id = 1")


def downgrade() -> None:
    op.drop_column("style_profiles", "default_enable_hr")
