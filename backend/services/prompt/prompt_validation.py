"""Prompt validation service for Gemini-generated prompts.

Validates tags against DB and Danbooru to detect risky/unknown tags.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from config import logger
from services.danbooru import get_tag_info_sync

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# Threshold for risky tags (Danbooru post count)
RISKY_TAG_THRESHOLD = 100  # Tags with <100 posts are considered risky

# Known problematic tags that should be replaced
# Maps non-Danbooru/risky tags to verified Danbooru alternatives
RISKY_TAG_REPLACEMENTS = {
    # Camera angles and framing
    # Key uses space format (user input), value uses underscore (Danbooru standard)
    "medium shot": "cowboy_shot",
    "medium_shot": "cowboy_shot",  # Also handle underscore input
    "close up": "close-up",
    "close_up": "close-up",
    "far shot": "from_distance",
    "far_shot": "from_distance",
    "wide shot": "from_distance",
    "wide_shot": "from_distance",
    "long shot": "full_body",
    "long_shot": "full_body",
    "extreme close-up": "portrait",
    "extreme_close-up": "portrait",
    "extreme closeup": "portrait",
    "extreme_closeup": "portrait",
    "birds eye view": "from_above",
    "birds_eye_view": "from_above",
    "bird's eye view": "from_above",
    "low angle": "from_below",
    "low_angle": "from_below",
    "high angle": "from_above",
    "high_angle": "from_above",
    "over the shoulder": "from_behind",
    "over_the_shoulder": "from_behind",
    "dutch angle": "tilted_angle",
    "dutch_angle": "tilted_angle",
    "point of view": "pov",
    "point_of_view": "pov",
    "first person view": "pov",
    "first_person_view": "pov",
    "third person view": "from_side",
    "third_person_view": "from_side",
    # Lighting (many SD-specific lighting terms don't exist in Danbooru)
    "soft lighting": "soft_light",
    "soft_lighting": "soft_light",
    "hard lighting": "dramatic_lighting",
    "hard_lighting": "dramatic_lighting",
    "natural lighting": "natural_light",
    "natural_lighting": "natural_light",
    "studio lighting": "studio_light",
    "studio_lighting": "studio_light",
    "rim lighting": "backlighting",
    "rim_lighting": "backlighting",
    "side lighting": "side_light",
    "side_lighting": "side_light",
    "top lighting": "light_from_above",
    "top_lighting": "light_from_above",
    "bottom lighting": "light_from_below",
    "bottom_lighting": "light_from_below",
    # Quality/Style (SD-specific, not Danbooru tags)
    "photorealistic": "realistic",
    "photo realistic": "realistic",
    "photo_realistic": "realistic",
    "ultra realistic": "realistic",
    "ultra_realistic": "realistic",
    "hyperrealistic": "realistic",
    "hyper realistic": "realistic",
    "hyper_realistic": "realistic",
    "4k": "high_resolution",
    "8k": "high_resolution",
    "hd": "high_resolution",
    "ultra hd": "high_resolution",
    "ultra_hd": "high_resolution",
    "unreal engine": None,  # Remove rather than replace
    "unreal_engine": None,
    "octane render": None,  # Remove rather than replace
    "octane_render": None,
    "ray tracing": None,  # Remove rather than replace
    "ray_tracing": None,
    # Composition
    "rule of thirds": "dynamic_composition",
    "rule_of_thirds": "dynamic_composition",
    "centered composition": "centered",
    "centered_composition": "centered",
    "symmetrical composition": "symmetry",
    "symmetrical_composition": "symmetry",
    "golden ratio": "dynamic_composition",
    "golden_ratio": "dynamic_composition",
    # Common typos and variations
    "bokeh effect": "bokeh",
    "bokeh_effect": "bokeh",
    "lens flare effect": "lens_flare",
    "lens_flare_effect": "lens_flare",
    "depth of field": "depth_of_field",
    "depth_of_field": "depth_of_field",
    # Appearance / Character (Composite to Individual)
    "short_green_hair": "short_hair, green_hair",
    "long_blonde_hair": "long_hair, blonde_hair",
    "medium_brown_hair": "medium_hair, brown_hair",
    "short_blue_hair": "short_hair, blue_hair",
    "short_red_hair": "short_hair, red_hair",
    "short_white_hair": "short_hair, white_hair",
    "short_black_hair": "short_hair, black_hair",
    "playing_guitar": "guitar, musical_instrument",
    "playing guitar": "guitar, musical_instrument",
}


def validate_prompt_tags(
    tags: list[str],
    db: Session,
    check_danbooru: bool = True,
) -> dict[str, Any]:
    """Validate prompt tags against DB and Danbooru.

    Args:
        tags: List of tag names to validate
        db: Database session
        check_danbooru: Whether to check Danbooru for unknown tags

    Returns:
        {
            "valid": [...],          # Tags found in DB
            "risky": [...],          # Tags with low Danbooru post counts or known problematic
            "unknown": [...],        # Tags not in DB and not in Danbooru
            "warnings": [            # List of warning messages
                {"tag": "medium shot", "reason": "...", "suggestion": "cowboy shot"},
                ...
            ]
        }
    """
    from models.tag import Tag

    valid_tags = []
    risky_tags = []
    unknown_tags = []
    warnings = []

    # Check against DB
    db_tags = db.query(Tag).filter(Tag.name.in_(tags)).all()
    db_tag_names = {t.name for t in db_tags}

    for tag in tags:
        # Known in DB
        if tag in db_tag_names:
            valid_tags.append(tag)
            continue

        # Known problematic tag with replacement
        if tag in RISKY_TAG_REPLACEMENTS:
            risky_tags.append(tag)
            warnings.append({
                "tag": tag,
                "reason": "Not a valid Danbooru tag (0 posts)",
                "suggestion": RISKY_TAG_REPLACEMENTS[tag],
            })
            continue

        # Check Danbooru if enabled
        if check_danbooru:
            try:
                # Optimized check: Skip API for known internal quality/style tags
                from services.keywords import CATEGORY_PATTERNS
                normalized_tag = tag.lower().replace(" ", "_")
                if normalized_tag in CATEGORY_PATTERNS.get("quality", []) or normalized_tag in CATEGORY_PATTERNS.get("style", []):
                    valid_tags.append(tag)
                    continue

                tag_info = get_tag_info_sync(tag)

                if tag_info:
                    post_count = tag_info.get("post_count", 0)

                    if post_count == 0:
                        risky_tags.append(tag)
                        warnings.append({
                            "tag": tag,
                            "reason": "Tag exists in Danbooru but has 0 posts",
                            "suggestion": None,
                        })
                    elif post_count < RISKY_TAG_THRESHOLD:
                        risky_tags.append(tag)
                        warnings.append({
                            "tag": tag,
                            "reason": f"Low usage in Danbooru ({post_count} posts)",
                            "suggestion": None,
                        })
                    else:
                        # Tag is valid in Danbooru with good usage
                        valid_tags.append(tag)
                else:
                    # Tag not found in Danbooru
                    unknown_tags.append(tag)
                    warnings.append({
                        "tag": tag,
                        "reason": "Tag not found in DB or Danbooru",
                        "suggestion": None,
                    })
            except Exception as exc:
                logger.warning(f"Failed to check Danbooru for tag '{tag}': {exc}")
                unknown_tags.append(tag)
                warnings.append({
                    "tag": tag,
                    "reason": "Failed to verify tag (Danbooru API error)",
                    "suggestion": None,
                })
        else:
            # Danbooru check disabled, mark as unknown
            unknown_tags.append(tag)
            warnings.append({
                "tag": tag,
                "reason": "Tag not found in DB",
                "suggestion": None,
            })

    return {
        "valid": valid_tags,
        "risky": risky_tags,
        "unknown": unknown_tags,
        "warnings": warnings,
        "total_tags": len(tags),
        "valid_count": len(valid_tags),
        "risky_count": len(risky_tags),
        "unknown_count": len(unknown_tags),
    }


def auto_replace_risky_tags(tags: list[str]) -> dict[str, Any]:
    """Automatically replace known risky tags with safe alternatives.

    Args:
        tags: List of tag names

    Returns:
        {
            "original": [...],
            "replaced": [...],
            "replacements": [{"from": "medium shot", "to": "cowboy shot"}, ...],
            "removed": [...]  # Tags that were removed (replacement was None)
        }
    """
    replaced = []
    replacements = []
    removed = []

    for tag in tags:
        if tag in RISKY_TAG_REPLACEMENTS:
            replacement = RISKY_TAG_REPLACEMENTS[tag]
            if replacement is None:
                # Tag should be removed, not replaced
                removed.append(tag)
                replacements.append({"from": tag, "to": None, "action": "removed"})
            else:
                # Tag should be replaced
                replaced.append(replacement)
                replacements.append({"from": tag, "to": replacement, "action": "replaced"})
        else:
            # Tag is safe, keep it
            replaced.append(tag)

    return {
        "original": tags,
        "replaced": replaced,
        "replacements": replacements,
        "removed": removed,
        "replaced_count": len([r for r in replacements if r["action"] == "replaced"]),
        "removed_count": len(removed),
    }


def check_tag_conflicts(tags: list[str], db: Session) -> dict:
    """Check for tag conflicts using DB rules.

    Args:
        tags: List of tag names to check
        db: Database session

    Returns:
        {
            "has_conflicts": bool,
            "conflicts": [
                {"tag1": str, "tag2": str}
            ],
            "filtered_tags": list[str]  # Tags with second conflicting tag removed
        }
    """
    from models.tag import Tag, TagRule

    # Normalize tags
    tag_names = [t.lower().strip() for t in tags if t]

    # Get tag IDs from DB
    tag_objects = db.query(Tag).filter(Tag.name.in_(tag_names)).all()
    tag_id_map = {tag.name: tag.id for tag in tag_objects}
    tag_name_map = {tag.id: tag.name for tag in tag_objects}

    # Get all conflict rules
    conflict_rules = db.query(TagRule).filter(TagRule.rule_type == "conflict").all()

    # Check for conflicts
    conflicts = []
    tags_to_remove = set()
    seen_pairs = set()  # Track seen conflict pairs to avoid duplicates

    for rule in conflict_rules:
        tag1_id = rule.source_tag_id
        tag2_id = rule.target_tag_id

        if tag1_id in tag_name_map and tag2_id in tag_name_map:
            tag1_name = tag_name_map[tag1_id]
            tag2_name = tag_name_map[tag2_id]

            # Check if both tags are in the input
            if tag1_name in tag_names and tag2_name in tag_names:
                # Create a normalized pair key to avoid duplicates
                pair_key = tuple(sorted([tag1_name, tag2_name]))

                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    conflicts.append({
                        "tag1": tag1_name,
                        "tag2": tag2_name,
                    })

                # Remove the second occurrence (keep first tag, remove second)
                if tag_names.index(tag1_name) < tag_names.index(tag2_name):
                    tags_to_remove.add(tag2_name)
                else:
                    tags_to_remove.add(tag1_name)

    # Filter out conflicting tags
    filtered_tags = [t for t in tags if t.lower().strip() not in tags_to_remove]

    logger.info(
        "[check_tag_conflicts] Found %d conflicts in %d tags, removed %d",
        len(conflicts),
        len(tags),
        len(tags_to_remove),
    )

    return {
        "has_conflicts": len(conflicts) > 0,
        "conflicts": conflicts,
        "filtered_tags": filtered_tags,
        "removed_tags": list(tags_to_remove),
    }
