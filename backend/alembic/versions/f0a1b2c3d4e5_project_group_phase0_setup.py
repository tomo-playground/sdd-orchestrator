"""Project/Group Phase 0 setup: render defaults, storyboards.group_id

Revision ID: f0a1b2c3d4e5
Revises: a1b2c3d4e5f6
Create Date: 2026-02-02 02:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0a1b2c3d4e5"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. projects 보정 (created_at NULL 수정)
    op.execute(text("UPDATE projects SET created_at=now(), updated_at=now() WHERE created_at IS NULL"))

    # 2. projects.handle partial unique index
    op.create_index(
        "ix_projects_handle",
        "projects",
        ["handle"],
        unique=True,
        postgresql_where=text("handle IS NOT NULL"),
    )

    # 3. groups 테이블에 render default 컬럼 추가
    op.add_column("groups", sa.Column("default_bgm_volume", sa.Float))
    op.add_column("groups", sa.Column("default_audio_ducking", sa.Boolean))
    op.add_column("groups", sa.Column("default_scene_text_font", sa.String(255)))
    op.add_column("groups", sa.Column("default_layout_style", sa.String(50)))
    op.add_column("groups", sa.Column("default_frame_style", sa.String(255)))
    op.add_column("groups", sa.Column("default_transition_type", sa.String(50)))
    op.add_column("groups", sa.Column("default_ken_burns_preset", sa.String(50)))
    op.add_column("groups", sa.Column("default_ken_burns_intensity", sa.Float))
    op.add_column("groups", sa.Column("default_speed_multiplier", sa.Float))

    # 4. groups FK 인덱스
    op.create_index("ix_groups_project_id", "groups", ["project_id"])

    # 5. storyboards.group_id 추가 (nullable first)
    op.add_column("storyboards", sa.Column("group_id", sa.Integer, nullable=True))

    # 6. Seed: Default Group 생성
    op.execute(
        text("""
        INSERT INTO groups (project_id, name, created_at, updated_at)
        VALUES (1, 'Default Series', now(), now())
    """)
    )

    # 7. 기존 storyboards 연결
    op.execute(
        text("""
        UPDATE storyboards SET group_id = (
            SELECT id FROM groups WHERE project_id=1 AND name='Default Series' LIMIT 1
        ) WHERE group_id IS NULL
    """)
    )

    # 8. NOT NULL 강제 + FK + 인덱스
    op.alter_column("storyboards", "group_id", nullable=False)
    op.create_foreign_key(
        "fk_storyboards_group_id",
        "storyboards",
        "groups",
        ["group_id"],
        ["id"],
    )
    op.create_index("ix_storyboards_group_id", "storyboards", ["group_id"])

    # 9. 시퀀스 리셋
    op.execute(text("SELECT setval('groups_id_seq', (SELECT COALESCE(MAX(id),1) FROM groups))"))


def downgrade() -> None:
    """Downgrade schema."""
    # storyboards.group_id 제거
    op.drop_index("ix_storyboards_group_id", table_name="storyboards")
    op.drop_constraint("fk_storyboards_group_id", "storyboards", type_="foreignkey")
    op.drop_column("storyboards", "group_id")

    # groups FK 인덱스 제거
    op.drop_index("ix_groups_project_id", table_name="groups")

    # groups render default 컬럼 제거
    op.drop_column("groups", "default_speed_multiplier")
    op.drop_column("groups", "default_ken_burns_intensity")
    op.drop_column("groups", "default_ken_burns_preset")
    op.drop_column("groups", "default_transition_type")
    op.drop_column("groups", "default_frame_style")
    op.drop_column("groups", "default_layout_style")
    op.drop_column("groups", "default_scene_text_font")
    op.drop_column("groups", "default_audio_ducking")
    op.drop_column("groups", "default_bgm_volume")

    # Default Series 삭제
    op.execute(text("DELETE FROM groups WHERE name='Default Series' AND project_id=1"))

    # projects.handle 인덱스 제거
    op.drop_index("ix_projects_handle", table_name="projects")
