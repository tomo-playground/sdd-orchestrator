"""Migrate custom_base_prompt and custom_negative_prompt for existing characters.

This script initializes the custom prompt fields based on character/LoRA characteristics.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from config import logger
from database import SessionLocal
from models import Character, LoRA


# Character-specific prompt templates
CHARACTER_PROMPTS = {
    "Blindbox": {
        "base_prompt": "chibi, cute, simple background, toy-like, rounded features",
        "negative_prompt": "realistic, detailed background, complex shading, human proportions",
    },
    "Chibi": {
        "base_prompt": "chibi, SD character, cute, simplified features, large head, small body",
        "negative_prompt": "realistic, detailed anatomy, normal proportions",
    },
    "Eureka": {
        "base_prompt": "anime style, detailed hair, expressive eyes, clean lineart",
        "negative_prompt": "",
    },
    "Eureka Blindbox": {
        "base_prompt": "chibi, cute, simple background, toy-like, rounded features",
        "negative_prompt": "realistic, detailed background, complex shading, human proportions",
    },
    "Eureka Chibi": {
        "base_prompt": "chibi, SD character, cute, simplified features, large head, small body",
        "negative_prompt": "realistic, detailed anatomy, normal proportions",
    },
    "Midoriya": {
        "base_prompt": "anime style, detailed hair, expressive eyes, clean lineart",
        "negative_prompt": "",
    },
    "Midoriya Chibi": {
        "base_prompt": "chibi, SD character, cute, simplified features, large head, small body",
        "negative_prompt": "realistic, detailed anatomy, normal proportions",
    },
    "Generic Anime Girl": {
        "base_prompt": "1girl, brown_hair, long_hair, brown_eyes, school_uniform, innocent_face",
        "negative_prompt": "nsfw, revealing_clothes, sexy, mature_female, heavy_makeup",
        "reference_base_prompt": "masterpiece, best quality, 1girl, solo, brown_hair, long_hair, brown_eyes, school_uniform, looking_at_viewer, simple_background, white_background, upper_body, innocent_smile, clean_lineart",
        "reference_negative_prompt": "verybadimagenegative_v1.3, easynegative, (worst quality, low quality:1.4), nsfw, revealing_clothes, sexy, mature_female, blurry, text, watermark",
    },
    "Generic Anime Boy": {
        "base_prompt": "1boy, black_hair, short_hair, brown_eyes, school_uniform, gentle_face",
        "negative_prompt": "nsfw, muscular, shirtless, mature_male, facial_hair",
        "reference_base_prompt": "masterpiece, best quality, 1boy, solo, black_hair, short_hair, brown_eyes, school_uniform, looking_at_viewer, simple_background, white_background, upper_body, gentle_smile, clean_lineart",
        "reference_negative_prompt": "verybadimagenegative_v1.3, easynegative, (worst quality, low quality:1.4), nsfw, muscular, shirtless, mature_male, blurry, text, watermark",
    },
}


def migrate_custom_prompts(db: Session, dry_run: bool = True) -> None:
    """Migrate custom prompts for existing characters.

    Args:
        db: Database session
        dry_run: If True, only show what would be changed without committing
    """
    characters = db.query(Character).all()
    updated_count = 0

    for character in characters:
        # Skip if user has already set custom prompts (SSOT: Character Edit Modal)
        if character.custom_base_prompt or character.custom_negative_prompt:
            logger.info(
                "⏭️  [%s] User has set custom prompts, skipping (SSOT: UI)",
                character.name,
            )
            continue

        # Get template for this character

        # Get template for this character
        template = CHARACTER_PROMPTS.get(character.name)
        if not template:
            logger.warning(
                "⚠️  [%s] No template found, skipping",
                character.name,
            )
            continue

        # Update custom prompts
        character.custom_base_prompt = template["base_prompt"] or None
        character.custom_negative_prompt = template["negative_prompt"] or None

        # Update reference prompts if provided in template
        if "reference_base_prompt" in template:
            character.reference_base_prompt = template["reference_base_prompt"] or None
        if "reference_negative_prompt" in template:
            character.reference_negative_prompt = template["reference_negative_prompt"] or None

        logger.info(
            "✅ [%s] Set prompts:\n  Custom Base: %s\n  Custom Negative: %s\n  Reference Base: %s\n  Reference Negative: %s",
            character.name,
            character.custom_base_prompt,
            character.custom_negative_prompt or "(empty)",
            character.reference_base_prompt[:50] + "..." if character.reference_base_prompt else "(unchanged)",
            character.reference_negative_prompt[:50] + "..." if character.reference_negative_prompt else "(unchanged)",
        )
        updated_count += 1

    if dry_run:
        logger.info("🔍 DRY RUN - No changes committed")
        db.rollback()
    else:
        db.commit()
        logger.info("💾 Committed %d character updates", updated_count)


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate custom prompts for characters")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to database (default is dry-run)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        migrate_custom_prompts(db, dry_run=not args.apply)
    finally:
        db.close()


if __name__ == "__main__":
    main()
