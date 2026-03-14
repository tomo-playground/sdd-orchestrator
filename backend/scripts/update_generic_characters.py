"""Update Generic Anime Girl/Boy prompts to simple, innocent style.

This script updates both custom prompts and reference prompts for Generic characters.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from config import logger
from database import SessionLocal
from models import Character

# Generic character prompts (simple, innocent style)
GENERIC_PROMPTS = {
    "Generic Anime Girl": {
        "custom_base_prompt": "1girl, brown_hair, long_hair, brown_eyes, school_uniform, innocent_face",
        "custom_negative_prompt": "nsfw, revealing_clothes, sexy, mature_female, heavy_makeup",
        "reference_base_prompt": "masterpiece, best quality, (1girl:1.3), (solo:1.3), brown_hair, long_hair, brown_eyes, school_uniform, looking_at_viewer, simple_background, white_background, upper_body, innocent_smile, clean_lineart",
        "reference_negative_prompt": "worst quality, low quality, lowres, bad anatomy, (multiple_girls:1.5), (2girls:1.5), (multiple_people:1.5), nsfw, revealing_clothes, sexy, mature_female, blurry, text, watermark",
    },
    "Generic Anime Boy": {
        "custom_base_prompt": "1boy, male_focus, black_hair, short_hair, brown_eyes, masculine, school_uniform",
        "custom_negative_prompt": "nsfw, feminine, breasts, long_eyelashes, lipstick, makeup, muscular, shirtless, mature_male, facial_hair",
        "reference_base_prompt": "masterpiece, best quality, (1boy:1.3), (solo:1.3), (male_focus:1.2), black_hair, short_hair, brown_eyes, masculine, school_uniform, blazer, looking_at_viewer, simple_background, white_background, upper_body, neutral_expression, clean_lineart",
        "reference_negative_prompt": "worst quality, low quality, lowres, bad anatomy, (multiple_boys:1.5), (2boys:1.5), (multiple_people:1.5), nsfw, feminine, breasts, long_eyelashes, lipstick, makeup, muscular, shirtless, mature_male, blurry, text, watermark",
    },
}


def update_generic_characters(db: Session, dry_run: bool = True) -> None:
    """Update Generic Anime Girl/Boy prompts.

    Args:
        db: Database session
        dry_run: If True, only show what would be changed without committing
    """
    updated_count = 0

    for char_name, prompts in GENERIC_PROMPTS.items():
        character = db.query(Character).filter(Character.name == char_name).first()

        if not character:
            logger.warning("⚠️  [%s] Character not found in database", char_name)
            continue

        # Update all prompts
        character.custom_base_prompt = prompts["custom_base_prompt"]
        character.custom_negative_prompt = prompts["custom_negative_prompt"]
        character.reference_base_prompt = prompts["reference_base_prompt"]
        character.reference_negative_prompt = prompts["reference_negative_prompt"]

        # Clear identity_tags and clothing_tags (all info is in prompts now)
        character.identity_tags = []
        character.clothing_tags = []
        character.loras = []

        logger.info(
            "✅ [%s] Updated prompts:\n"
            "  Custom Base: %s\n"
            "  Custom Negative: %s\n"
            "  Reference Base: %s...\n"
            "  Reference Negative: %s...",
            char_name,
            character.custom_base_prompt,
            character.custom_negative_prompt,
            character.reference_base_prompt[:70],
            character.reference_negative_prompt[:70],
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

    parser = argparse.ArgumentParser(description="Update Generic Anime Girl/Boy prompts")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to database (default is dry-run)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        update_generic_characters(db, dry_run=not args.apply)
    finally:
        db.close()


if __name__ == "__main__":
    main()
