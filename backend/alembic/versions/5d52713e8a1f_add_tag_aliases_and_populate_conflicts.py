"""add_tag_aliases_and_populate_conflicts

Revision ID: 5d52713e8a1f
Revises: 301bc8eb327e
Create Date: 2026-01-29 12:53:54.047031

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d52713e8a1f"
down_revision: str | Sequence[str] | None = "301bc8eb327e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create tag_aliases table
    op.create_table(
        "tag_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_tag", sa.String(100), nullable=False),
        sa.Column("target_tag", sa.String(100), nullable=True),  # NULL = remove tag
        sa.Column("reason", sa.String(200), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tag_aliases_source_tag", "tag_aliases", ["source_tag"])

    # Populate with RISKY_TAG_REPLACEMENTS
    connection = op.get_bind()

    # Camera angles and framing
    aliases = [
        ("medium shot", "cowboy_shot", "Camera: Non-Danbooru term"),
        ("medium_shot", "cowboy_shot", "Camera: Non-Danbooru term"),
        ("close up", "close-up", "Camera: Spacing correction"),
        ("close_up", "close-up", "Camera: Spacing correction"),
        ("far shot", "from_distance", "Camera: Non-Danbooru term"),
        ("far_shot", "from_distance", "Camera: Non-Danbooru term"),
        ("wide shot", "from_distance", "Camera: Non-Danbooru term"),
        ("wide_shot", "from_distance", "Camera: Non-Danbooru term"),
        ("long shot", "full_body", "Camera: Non-Danbooru term"),
        ("long_shot", "full_body", "Camera: Non-Danbooru term"),
        ("extreme close-up", "portrait", "Camera: Non-Danbooru term"),
        ("extreme_close-up", "portrait", "Camera: Non-Danbooru term"),
        ("extreme closeup", "portrait", "Camera: Non-Danbooru term"),
        ("extreme_closeup", "portrait", "Camera: Non-Danbooru term"),
        ("birds eye view", "from_above", "Camera: Non-Danbooru term"),
        ("birds_eye_view", "from_above", "Camera: Non-Danbooru term"),
        ("bird's eye view", "from_above", "Camera: Non-Danbooru term"),
        ("low angle", "from_below", "Camera: Non-Danbooru term"),
        ("low_angle", "from_below", "Camera: Non-Danbooru term"),
        ("high angle", "from_above", "Camera: Non-Danbooru term"),
        ("high_angle", "from_above", "Camera: Non-Danbooru term"),
        ("over the shoulder", "from_behind", "Camera: Non-Danbooru term"),
        ("over_the_shoulder", "from_behind", "Camera: Non-Danbooru term"),
        ("dutch angle", "tilted_angle", "Camera: Non-Danbooru term"),
        ("dutch_angle", "tilted_angle", "Camera: Non-Danbooru term"),
        ("point of view", "pov", "Camera: Non-Danbooru term"),
        ("point_of_view", "pov", "Camera: Non-Danbooru term"),
        ("first person view", "pov", "Camera: Non-Danbooru term"),
        ("first_person_view", "pov", "Camera: Non-Danbooru term"),
        ("third person view", "from_side", "Camera: Non-Danbooru term"),
        ("third_person_view", "from_side", "Camera: Non-Danbooru term"),
        # Lighting
        ("soft lighting", "soft_light", "Lighting: Non-Danbooru term"),
        ("soft_lighting", "soft_light", "Lighting: Non-Danbooru term"),
        ("hard lighting", "dramatic_lighting", "Lighting: Non-Danbooru term"),
        ("hard_lighting", "dramatic_lighting", "Lighting: Non-Danbooru term"),
        ("natural lighting", "natural_light", "Lighting: Non-Danbooru term"),
        ("natural_lighting", "natural_light", "Lighting: Non-Danbooru term"),
        ("studio lighting", "studio_light", "Lighting: Non-Danbooru term"),
        ("studio_lighting", "studio_light", "Lighting: Non-Danbooru term"),
        ("rim lighting", "backlighting", "Lighting: Non-Danbooru term"),
        ("rim_lighting", "backlighting", "Lighting: Non-Danbooru term"),
        ("side lighting", "side_light", "Lighting: Non-Danbooru term"),
        ("side_lighting", "side_light", "Lighting: Non-Danbooru term"),
        ("top lighting", "light_from_above", "Lighting: Non-Danbooru term"),
        ("top_lighting", "light_from_above", "Lighting: Non-Danbooru term"),
        ("bottom lighting", "light_from_below", "Lighting: Non-Danbooru term"),
        ("bottom_lighting", "light_from_below", "Lighting: Non-Danbooru term"),
        # Quality/Style (SD-specific)
        ("photorealistic", "realistic", "Quality: SD-specific term"),
        ("photo realistic", "realistic", "Quality: SD-specific term"),
        ("photo_realistic", "realistic", "Quality: SD-specific term"),
        ("ultra realistic", "realistic", "Quality: SD-specific term"),
        ("ultra_realistic", "realistic", "Quality: SD-specific term"),
        ("hyperrealistic", "realistic", "Quality: SD-specific term"),
        ("hyper realistic", "realistic", "Quality: SD-specific term"),
        ("hyper_realistic", "realistic", "Quality: SD-specific term"),
        ("4k", "high_resolution", "Quality: SD-specific term"),
        ("8k", "high_resolution", "Quality: SD-specific term"),
        ("hd", "high_resolution", "Quality: SD-specific term"),
        ("ultra hd", "high_resolution", "Quality: SD-specific term"),
        ("ultra_hd", "high_resolution", "Quality: SD-specific term"),
        ("unreal engine", None, "Quality: Remove (SD-specific)"),
        ("unreal_engine", None, "Quality: Remove (SD-specific)"),
        ("octane render", None, "Quality: Remove (SD-specific)"),
        ("octane_render", None, "Quality: Remove (SD-specific)"),
        ("ray tracing", None, "Quality: Remove (SD-specific)"),
        ("ray_tracing", None, "Quality: Remove (SD-specific)"),
        # Composition
        ("rule of thirds", "dynamic_composition", "Composition: Non-Danbooru term"),
        ("rule_of_thirds", "dynamic_composition", "Composition: Non-Danbooru term"),
        ("centered composition", "centered", "Composition: Non-Danbooru term"),
        ("centered_composition", "centered", "Composition: Non-Danbooru term"),
        ("symmetrical composition", "symmetry", "Composition: Non-Danbooru term"),
        ("symmetrical_composition", "symmetry", "Composition: Non-Danbooru term"),
        ("golden ratio", "dynamic_composition", "Composition: Non-Danbooru term"),
        ("golden_ratio", "dynamic_composition", "Composition: Non-Danbooru term"),
        # Common typos and variations
        ("bokeh effect", "bokeh", "Typo: Redundant 'effect'"),
        ("bokeh_effect", "bokeh", "Typo: Redundant 'effect'"),
        ("lens flare effect", "lens_flare", "Typo: Redundant 'effect'"),
        ("lens_flare_effect", "lens_flare", "Typo: Redundant 'effect'"),
        ("depth of field", "depth_of_field", "Typo: Spacing correction"),
        ("depth_of_field", "depth_of_field", "Typo: Already correct"),
        # Appearance / Character (Composite to Individual)
        ("short_green_hair", "short_hair, green_hair", "Composite: Split into components"),
        ("long_blonde_hair", "long_hair, blonde_hair", "Composite: Split into components"),
        ("medium_brown_hair", "medium_hair, brown_hair", "Composite: Split into components"),
        ("short_blue_hair", "short_hair, blue_hair", "Composite: Split into components"),
        ("short_red_hair", "short_hair, red_hair", "Composite: Split into components"),
        ("short_white_hair", "short_hair, white_hair", "Composite: Split into components"),
        ("short_black_hair", "short_hair, black_hair", "Composite: Split into components"),
        ("playing_guitar", "guitar, musical_instrument", "Composite: Split into components"),
        ("playing guitar", "guitar, musical_instrument", "Composite: Split into components"),
    ]

    for source, target, reason in aliases:
        connection.execute(
            sa.text("""
                INSERT INTO tag_aliases (source_tag, target_tag, reason, active)
                VALUES (:source, :target, :reason, true)
            """),
            {"source": source, "target": target, "reason": reason},
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_tag_aliases_source_tag", "tag_aliases")
    op.drop_table("tag_aliases")
