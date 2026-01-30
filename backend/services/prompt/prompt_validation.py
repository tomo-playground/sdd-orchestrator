"""Prompt validation service for Gemini-generated prompts.

Validates tags against DB and Danbooru to detect risky/unknown tags.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from config import logger
from services.danbooru import get_tag_info_sync
from services.keywords.db_cache import TagAliasCache

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# Threshold for risky tags (Danbooru post count)
RISKY_TAG_THRESHOLD = 100  # Tags with <100 posts are considered risky

# RISKY_TAG_REPLACEMENTS is now managed in the database (tag_aliases table)
# and accessed via TagAliasCache


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

        # Check TagAliasCache for known replacements
        replacement = TagAliasCache.get_replacement(tag)
        if replacement is not ...:
            risky_tags.append(tag)
            warnings.append({
                "tag": tag,
                "reason": "Invalid or risky tag, replaced with verified alternative",
                "suggestion": replacement,
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
        replacement = TagAliasCache.get_replacement(tag)
        if replacement is not ...:
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
