"""Add IP-Adapter enhancement columns to characters

Phase 1~3 IP-Adapter 캐릭터 유사도 고도화:
- reference_source_type: "generated" | "uploaded" (Phase 1-A)
- reference_images: JSONB multi-angle references (Phase 2-A)
- ip_adapter_guidance_start: Per-character guidance start (Phase 3-A)
- ip_adapter_guidance_end: Per-character guidance end (Phase 3-A)

All nullable → 100% backward compatible.

Revision ID: l9e0f1g2h3i4
Revises: k8d9e0f1g2h3
Create Date: 2026-02-22 02:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "l9e0f1g2h3i4"
down_revision = "k8d9e0f1g2h3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("reference_source_type", sa.String(20), nullable=True))
    op.add_column("characters", sa.Column("reference_images", JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("characters", sa.Column("ip_adapter_guidance_start", sa.Float(), nullable=True))
    op.add_column("characters", sa.Column("ip_adapter_guidance_end", sa.Float(), nullable=True))
    op.create_check_constraint(
        "ck_characters_reference_source_type",
        "characters",
        "reference_source_type IN ('generated', 'uploaded')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_characters_reference_source_type", "characters", type_="check")
    op.drop_column("characters", "ip_adapter_guidance_end")
    op.drop_column("characters", "ip_adapter_guidance_start")
    op.drop_column("characters", "reference_images")
    op.drop_column("characters", "reference_source_type")
