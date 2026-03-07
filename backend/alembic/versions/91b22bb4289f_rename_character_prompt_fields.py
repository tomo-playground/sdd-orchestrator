"""Rename character prompt fields for clarity.

custom_base_prompt -> scene_positive_prompt
custom_negative_prompt -> scene_negative_prompt
reference_base_prompt -> reference_positive_prompt
recommended_negative -> common_negative_prompts

Revision ID: 91b22bb4289f
Revises: y7z8a9b0c1d2
Create Date: 2026-03-07
"""

from alembic import op

revision = "91b22bb4289f"
down_revision = "y7z8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("characters", "custom_base_prompt", new_column_name="scene_positive_prompt")
    op.alter_column("characters", "custom_negative_prompt", new_column_name="scene_negative_prompt")
    op.alter_column("characters", "reference_base_prompt", new_column_name="reference_positive_prompt")
    op.alter_column("characters", "recommended_negative", new_column_name="common_negative_prompts")


def downgrade() -> None:
    op.alter_column("characters", "scene_positive_prompt", new_column_name="custom_base_prompt")
    op.alter_column("characters", "scene_negative_prompt", new_column_name="custom_negative_prompt")
    op.alter_column("characters", "reference_positive_prompt", new_column_name="reference_base_prompt")
    op.alter_column("characters", "common_negative_prompts", new_column_name="recommended_negative")
