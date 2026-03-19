"""Migrate reference_base_prompt and reference_negative_prompt for existing characters.

This script initializes the reference prompt fields with default values
for all characters that don't have them set.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from config import logger
from database import SessionLocal
from models import Character

# Default reference prompts (moved from controlnet.py hardcoding)
DEFAULT_REFERENCE_BASE = "masterpiece, best quality, anime portrait, clean background, head and shoulders, looking at viewer, front view, facing front, eye contact, simple background, white background"

DEFAULT_REFERENCE_NEGATIVE = (
    "worst quality, low quality, lowres, bad anatomy, blurry, text, watermark, from side, from behind, profile"
)


def migrate_reference_prompts(db: Session, dry_run: bool = True) -> None:
    """Migrate reference prompts for existing characters.

    Args:
        db: Database session
        dry_run: If True, only show what would be changed without committing
    """
    characters = db.query(Character).all()
    updated_count = 0

    for character in characters:
        changed = False

        # Set reference_base_prompt if not set
        if not character.reference_base_prompt:
            character.reference_base_prompt = DEFAULT_REFERENCE_BASE
            changed = True

        # Set reference_negative_prompt if not set
        if not character.reference_negative_prompt:
            character.reference_negative_prompt = DEFAULT_REFERENCE_NEGATIVE
            changed = True

        if changed:
            logger.info(
                "✅ [%s] Set reference prompts:\n  Base: %s\n  Negative: %s",
                character.name,
                character.reference_base_prompt[:80] + "..."
                if len(character.reference_base_prompt) > 80
                else character.reference_base_prompt,
                character.reference_negative_prompt[:80] + "..."
                if len(character.reference_negative_prompt) > 80
                else character.reference_negative_prompt,
            )
            updated_count += 1
        else:
            logger.info(
                "⏭️  [%s] Already has reference prompts, skipping",
                character.name,
            )

    if dry_run:
        logger.info("🔍 DRY RUN - No changes committed")
        db.rollback()
    else:
        db.commit()
        logger.info("💾 Committed %d character updates", updated_count)


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate reference prompts for characters")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to database (default is dry-run)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        migrate_reference_prompts(db, dry_run=not args.apply)
    finally:
        db.close()


if __name__ == "__main__":
    main()
