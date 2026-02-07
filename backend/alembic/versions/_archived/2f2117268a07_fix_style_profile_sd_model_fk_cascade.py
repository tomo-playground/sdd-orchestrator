"""fix_style_profile_sd_model_fk_cascade

Revision ID: 2f2117268a07
Revises: e1fd14c87f7b
Create Date: 2026-02-06 19:11:03.595201

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2f2117268a07"
down_revision: Union[str, Sequence[str], None] = "e1fd14c87f7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change style_profiles.sd_model_id FK from NO ACTION to SET NULL."""
    op.drop_constraint("style_profiles_sd_model_id_fkey", "style_profiles", type_="foreignkey")
    op.create_foreign_key(
        "style_profiles_sd_model_id_fkey",
        "style_profiles",
        "sd_models",
        ["sd_model_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Revert to NO ACTION."""
    op.drop_constraint("style_profiles_sd_model_id_fkey", "style_profiles", type_="foreignkey")
    op.create_foreign_key(
        "style_profiles_sd_model_id_fkey",
        "style_profiles",
        "sd_models",
        ["sd_model_id"],
        ["id"],
    )
