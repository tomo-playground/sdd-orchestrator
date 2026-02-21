"""Add default_ip_adapter_model to style_profiles

Style Profile 기반 IP-Adapter 모델 자동 선택을 위해
style_profiles 테이블에 default_ip_adapter_model 컬럼 추가.

- Anime 스타일 → clip_face (CLIP 기반)
- Realistic 스타일 → faceid (InsightFace 기반)

Revision ID: i6b7c8d9e0f1
Revises: h5a6b7c8d9e0
Create Date: 2026-02-21 18:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "i6b7c8d9e0f1"
down_revision = "h5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "style_profiles",
        sa.Column("default_ip_adapter_model", sa.String(20), nullable=True),
    )

    # Data migration: Realistic(id=2) → faceid, 나머지 → clip_face
    op.execute("UPDATE style_profiles SET default_ip_adapter_model = 'clip_face'")
    op.execute("UPDATE style_profiles SET default_ip_adapter_model = 'faceid' WHERE id = 2")


def downgrade() -> None:
    op.drop_column("style_profiles", "default_ip_adapter_model")
