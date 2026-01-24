"""expand_pose_expression_tags

Revision ID: e1f2g3h4i5j6
Revises: d073d96eed09
Create Date: 2026-01-24 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2g3h4i5j6'
down_revision: Union[str, Sequence[str], None] = 'd073d96eed09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tag reclassification: pose -> expression, gaze, pose, action
EXPRESSION_TAGS = [
    'angry', 'blush', 'closed eyes', 'crying', 'embarrassed',
    'expressionless', 'laughing', 'nervous', 'sad', 'scared',
    'serious', 'smile', 'surprised', 'wink'
]

GAZE_TAGS = [
    'looking at viewer', 'looking away', 'looking back',
    'looking down', 'looking up'
]

POSE_TAGS = ['kneeling', 'lying', 'sitting', 'standing']

ACTION_TAGS = [
    'dancing', 'drinking', 'eating', 'fighting', 'jumping',
    'reading', 'running', 'talking', 'walking'
]

# New Danbooru-based tags to add
NEW_EXPRESSION_TAGS = [
    'smirk', 'pout', 'frown', 'grin', 'open mouth', 'tears',
    'happy', 'sleepy', 'confused', 'annoyed', 'excited',
    'worried', 'determined', 'shy', 'bored'
]

NEW_GAZE_TAGS = [
    'looking to the side', 'eye contact', 'looking afar',
    'closed eyes', 'half-closed eyes', 'wide eyes'
]

NEW_POSE_TAGS = [
    'crouching', 'leaning', 'arms crossed', 'arms behind back',
    'hands on hips', 'hand on chest', 'hand on chin', 'pointing',
    'stretching', 'hugging knees', 'crossed legs', 'head tilt'
]

NEW_ACTION_TAGS = [
    'sleeping', 'crying', 'thinking', 'waving', 'cheering',
    'cooking', 'studying', 'working', 'playing', 'singing',
    'holding', 'reaching', 'falling', 'turning around'
]


def upgrade() -> None:
    """Upgrade: reclassify pose tags and add new Danbooru-based tags."""
    conn = op.get_bind()

    # 1. Reclassify existing tags
    for tag in EXPRESSION_TAGS:
        conn.execute(
            sa.text("UPDATE tags SET group_name = 'expression' WHERE name = :name AND category = 'scene'"),
            {'name': tag}
        )

    for tag in GAZE_TAGS:
        conn.execute(
            sa.text("UPDATE tags SET group_name = 'gaze' WHERE name = :name AND category = 'scene'"),
            {'name': tag}
        )

    for tag in POSE_TAGS:
        conn.execute(
            sa.text("UPDATE tags SET group_name = 'pose' WHERE name = :name AND category = 'scene'"),
            {'name': tag}
        )

    for tag in ACTION_TAGS:
        conn.execute(
            sa.text("UPDATE tags SET group_name = 'action' WHERE name = :name AND category = 'scene'"),
            {'name': tag}
        )

    # 2. Add new tags (skip if already exists)
    def insert_tag(name: str, group: str, priority: int = 0):
        conn.execute(
            sa.text("""
                INSERT INTO tags (name, category, group_name, priority, exclusive, created_at, updated_at)
                SELECT :name, 'scene', :group, :priority, false, NOW(), NOW()
                WHERE NOT EXISTS (SELECT 1 FROM tags WHERE name = :name AND category = 'scene')
            """),
            {'name': name, 'group': group, 'priority': priority}
        )

    for tag in NEW_EXPRESSION_TAGS:
        insert_tag(tag, 'expression')

    for tag in NEW_GAZE_TAGS:
        insert_tag(tag, 'gaze')

    for tag in NEW_POSE_TAGS:
        insert_tag(tag, 'pose')

    for tag in NEW_ACTION_TAGS:
        insert_tag(tag, 'action')


def downgrade() -> None:
    """Downgrade: revert to original pose group and remove new tags."""
    conn = op.get_bind()

    # 1. Revert group_name back to 'pose' for original tags
    all_original = EXPRESSION_TAGS + GAZE_TAGS + POSE_TAGS + ACTION_TAGS
    for tag in all_original:
        conn.execute(
            sa.text("UPDATE tags SET group_name = 'pose' WHERE name = :name AND category = 'scene'"),
            {'name': tag}
        )

    # 2. Remove newly added tags
    all_new = NEW_EXPRESSION_TAGS + NEW_GAZE_TAGS + NEW_POSE_TAGS + NEW_ACTION_TAGS
    for tag in all_new:
        conn.execute(
            sa.text("DELETE FROM tags WHERE name = :name AND category = 'scene'"),
            {'name': tag}
        )
