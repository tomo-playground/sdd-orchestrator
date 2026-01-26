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
    "medium shot": "cowboy shot",
    "close up": "close-up",
    "far shot": "from distance",
    "wide shot": "from distance",
    "long shot": "full body",
    "extreme close-up": "portrait",
    "extreme closeup": "portrait",
    "birds eye view": "from above",
    "bird's eye view": "from above",
    "low angle": "from below",
    "high angle": "from above",
    "over the shoulder": "from behind",
    "dutch angle": "tilted angle",
    "point of view": "pov",
    "first person view": "pov",
    "third person view": "from side",
    # Lighting (many SD-specific lighting terms don't exist in Danbooru)
    "soft lighting": "soft light",
    "hard lighting": "dramatic lighting",
    "natural lighting": "natural light",
    "studio lighting": "studio light",
    "rim lighting": "backlighting",
    "side lighting": "side light",
    "top lighting": "light from above",
    "bottom lighting": "light from below",
    # Quality/Style (SD-specific, not Danbooru tags)
    "photorealistic": "realistic",
    "photo realistic": "realistic",
    "ultra realistic": "realistic",
    "hyperrealistic": "realistic",
    "hyper realistic": "realistic",
    "4k": "high resolution",
    "8k": "high resolution",
    "hd": "high resolution",
    "ultra hd": "high resolution",
    "unreal engine": None,  # Remove rather than replace
    "octane render": None,  # Remove rather than replace
    "ray tracing": None,  # Remove rather than replace
    # Composition
    "rule of thirds": "dynamic composition",
    "centered composition": "centered",
    "symmetrical composition": "symmetry",
    "golden ratio": "dynamic composition",
    # Common typos and variations
    "bokeh effect": "bokeh",
    "lens flare effect": "lens flare",
    "depth of field": "depth of field",  # This one is OK, kept for consistency check
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
                "reason": f"Not a valid Danbooru tag (0 posts)",
                "suggestion": RISKY_TAG_REPLACEMENTS[tag],
            })
            continue

        # Check Danbooru if enabled
        if check_danbooru:
            try:
                tag_info = get_tag_info_sync(tag)

                if tag_info:
                    post_count = tag_info.get("post_count", 0)

                    if post_count == 0:
                        risky_tags.append(tag)
                        warnings.append({
                            "tag": tag,
                            "reason": f"Tag exists in Danbooru but has 0 posts",
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
