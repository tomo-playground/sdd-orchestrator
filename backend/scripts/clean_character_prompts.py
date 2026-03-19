import sys
from pathlib import Path
from typing import Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from config import logger
from database import SessionLocal
from models import Character, Tag
from services.keywords import CATEGORY_PATTERNS, normalize_prompt_token


# Helper to classify a tag into one of our custom categories for cleanup
# Returns 'style_quality', 'appearance', 'clothing', 'gender', 'scene_other', 'unknown'
def get_category_from_patterns(tag_name: str) -> str:
    """Classify a tag based on CATEGORY_PATTERNS."""
    normalized = normalize_prompt_token(tag_name)
    if not normalized:
        return "unknown"

    # Specific direct mappings for common tags that are always styles/quality
    if normalized in {
        "chibi",
        "super_deformed",
        "cute",
        "simple",
        "toy-like",
        "toy",
        "anime_style",
        "simple_background",
        "clean_lineart",
        "vibrant_colors",
        "clean_lines",
        "detailed_hair",
        "expressive_eyes",
        "anime_coloring",
        "detailed_eyes",
    }:
        return "style_quality"
    if normalized == "round_face" or normalized == "innocent_face" or "face" in normalized:
        return "appearance"
    if normalized == "full_body" or normalized == "upper_body" or normalized == "bust_shot":
        return "appearance"  # Treat as framing/body feature for character
    if "hair" in normalized or "eyes" in normalized or "skin" in normalized or "body" in normalized:
        return "appearance"
    if "dress" in normalized or "uniform" in normalized or "shirt" in normalized or "pants" in normalized:
        return "clothing"
    if "background" in normalized:
        return "style_quality"  # e.g., simple_background

    # Iterate through CATEGORY_PATTERNS for more general classification
    for category_group, patterns in CATEGORY_PATTERNS.items():
        if normalized in patterns:
            if category_group in {"quality", "style", "subject", "identity"}:
                return "style_quality"
            elif category_group in {
                "hair_color",
                "hair_length",
                "hair_style",
                "hair_accessory",
                "eye_color",
                "skin_color",
                "body_feature",
                "appearance",
            }:
                return "appearance"
            elif category_group == "clothing":
                return "clothing"
            elif category_group in {
                "expression",
                "gaze",
                "pose",
                "action",
                "camera",
                "location_indoor",
                "environment",
                "location_outdoor",
                "background_type",
                "time_weather",
                "lighting",
                "mood",
            }:
                return "scene_other"  # These should ideally not be in character base

    return "unknown"


def classify_tag_for_cleanup(tag_name: str, tag_db_info: dict[str, Any]) -> str:
    # Tags that should be explicitly filtered out
    gender_tags = {
        "1girl",
        "1boy",
        "1other",
        "male",
        "female",
        "man",
        "woman",
        "boy",
        "girl",
        "male_focus",
        "female_focus",
    }
    if normalize_prompt_token(tag_name) in gender_tags:
        return "gender"

    # Try to classify using DB info first (if synced via sync_category_patterns_to_tags)
    db_category = tag_db_info.get("category")
    db_group_name = tag_db_info.get("group_name")

    # Higher priority (lower number) in CATEGORY_PRIORITY usually means style/quality
    if db_group_name in {"quality", "style"} or (db_category == "quality") or (db_category == "style"):
        return "style_quality"

    # Character appearance-related
    if db_category == "character":
        if db_group_name in {
            "hair_color",
            "hair_length",
            "hair_style",
            "hair_accessory",
            "eye_color",
            "skin_color",
            "body_feature",
            "appearance",
            "identity",
        }:
            return "appearance"
        if db_group_name == "clothing":
            return "clothing"

    # If DB info is not precise enough, use pattern-based classification
    return get_category_from_patterns(tag_name)


def clean_character_prompts(db: Session, dry_run: bool = True) -> None:
    logger.info("🚀 Starting character prompt cleanup...")

    # Load all tags from DB for mapping
    all_tags = db.query(Tag).all()
    tag_name_to_id = {normalize_prompt_token(t.name): t.id for t in all_tags}
    tag_id_to_name = {t.id: normalize_prompt_token(t.name) for t in all_tags}
    tag_info_map = {
        normalize_prompt_token(t.name): {"category": t.category, "group_name": t.group_name} for t in all_tags
    }

    characters = db.query(Character).order_by(Character.name).all()
    updated_count = 0

    for character in characters:
        original_base_prompt = character.custom_base_prompt or ""
        original_identity_ids = character.identity_tags or []
        original_clothing_ids = character.clothing_tags or []

        all_collected_tokens: set[str] = set()

        # Collect tokens from custom_base_prompt
        if original_base_prompt:
            tokens_from_base = [normalize_prompt_token(t) for t in original_base_prompt.split(",") if t.strip()]
            all_collected_tokens.update(tokens_from_base)

        # Collect tokens from identity_tags
        tokens_from_identity = [tag_id_to_name[tid] for tid in original_identity_ids if tid in tag_id_to_name]
        all_collected_tokens.update(tokens_from_identity)

        # Collect tokens from clothing_tags
        tokens_from_clothing = [tag_id_to_name[tid] for tid in original_clothing_ids if tid in tag_id_to_name]
        all_collected_tokens.update(tokens_from_clothing)

        new_custom_base_prompt_tokens: list[str] = []
        new_identity_tag_names: list[str] = []  # Use names for easier management, convert to IDs at end
        new_clothing_tag_names: list[str] = []  # Use names for easier management, convert to IDs at end

        for token in sorted(all_collected_tokens):  # Sort for consistent order
            if not token:
                continue

            classification = classify_tag_for_cleanup(token, tag_info_map.get(token, {}))

            if classification == "gender":
                logger.debug(f"[{character.name}] Skipping gender tag: {token}")
                continue
            elif classification == "style_quality":
                new_custom_base_prompt_tokens.append(token)
            elif classification == "appearance":
                new_identity_tag_names.append(token)
            elif classification == "clothing":
                new_clothing_tag_names.append(token)
            elif classification == "scene_other":
                logger.warning(f"[{character.name}] Skipping scene-related tag found in character prompt: {token}")
                continue
            else:
                logger.warning(f"[{character.name}] Unknown tag classification for '{token}', skipping.")
                continue

        # Convert tag names back to IDs
        final_identity_tag_ids = sorted(
            [tag_name_to_id[name] for name in new_identity_tag_names if name in tag_name_to_id]
        )
        final_clothing_tag_ids = sorted(
            [tag_name_to_id[name] for name in new_clothing_tag_names if name in tag_name_to_id]
        )

        # New base prompt (sorted for consistency)
        new_base_prompt_string = ", ".join(sorted(new_custom_base_prompt_tokens))

        # Check for changes
        has_changes = False
        if new_base_prompt_string != original_base_prompt:
            logger.info(
                f"[{character.name}] custom_base_prompt changed: '{original_base_prompt}' -> '{new_base_prompt_string}'"
            )
            has_changes = True
        if set(final_identity_tag_ids) != set(original_identity_ids):
            logger.info(
                f"[{character.name}] identity_tags changed: {original_identity_ids} -> {final_identity_tag_ids}"
            )
            has_changes = True
        if set(final_clothing_tag_ids) != set(original_clothing_ids):
            logger.info(
                f"[{character.name}] clothing_tags changed: {original_clothing_ids} -> {final_clothing_tag_ids}"
            )
            has_changes = True

        if has_changes:
            character.custom_base_prompt = new_base_prompt_string
            character.identity_tags = final_identity_tag_ids
            character.clothing_tags = final_clothing_tag_ids
            updated_count += 1
        else:
            logger.info(f"[{character.name}] No changes needed.")

    if dry_run:
        logger.info("🔍 DRY RUN - No changes committed.")
        db.rollback()
    else:
        db.commit()
        logger.info(f"💾 Committed {updated_count} character updates.")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Clean up character prompt fields.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to the database (default is dry-run).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        clean_character_prompts(db, dry_run=not args.apply)
    finally:
        db.close()


if __name__ == "__main__":
    main()
