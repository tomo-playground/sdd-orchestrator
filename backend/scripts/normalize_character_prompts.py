"""Normalize character prompts to Danbooru standard (underscore format).

For tags that exist in DB: convert to underscore version
For custom text not in DB: keep as-is
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from config import logger
from database import SessionLocal
from models import Character, Tag


def normalize_prompt(prompt: str, db: Session) -> str:
    """Normalize a prompt to use underscore format for DB tags.

    Args:
        prompt: Comma-separated prompt string
        db: Database session

    Returns:
        Normalized prompt string
    """
    if not prompt:
        return prompt

    # Parse tokens
    tokens = [token.strip() for token in prompt.split(",")]
    normalized_tokens = []

    # Build tag lookup (both space and underscore versions)
    tag_map = {}  # "normalized_key" -> Tag object
    all_tags = db.query(Tag).all()

    for tag in all_tags:
        normalized_key = tag.name.replace("_", " ").lower()
        # Prefer underscore version if duplicate
        if normalized_key not in tag_map or "_" in tag.name:
            tag_map[normalized_key] = tag

    # Normalize each token
    for token in tokens:
        if not token:
            continue

        # Check if this token exists in DB
        normalized_key = token.replace("_", " ").lower()

        if normalized_key in tag_map:
            # Use DB version (underscore format)
            db_tag = tag_map[normalized_key]
            normalized_tokens.append(db_tag.name)
            logger.debug(f"  DB tag: {token} → {db_tag.name}")
        else:
            # Keep as-is (custom text)
            normalized_tokens.append(token)
            logger.debug(f"  Custom: {token}")

    return ", ".join(normalized_tokens)


def normalize_all_characters(db: Session, dry_run: bool = True) -> None:
    """Normalize prompts for all characters.

    Args:
        db: Database session
        dry_run: If True, only show what would be changed
    """
    characters = db.query(Character).order_by(Character.name).all()
    updated_count = 0

    for char in characters:
        changed = False
        logger.info(f"\n{'='*60}")
        logger.info(f"Character: {char.name}")

        # Normalize custom_base_prompt
        if char.custom_base_prompt:
            original = char.custom_base_prompt
            normalized = normalize_prompt(original, db)

            if original != normalized:
                logger.info(f"  custom_base_prompt:")
                logger.info(f"    Before: {original}")
                logger.info(f"    After:  {normalized}")
                char.custom_base_prompt = normalized
                changed = True
            else:
                logger.info(f"  custom_base_prompt: OK (no changes)")

        # Normalize reference_base_prompt
        if char.reference_base_prompt:
            original = char.reference_base_prompt
            normalized = normalize_prompt(original, db)

            if original != normalized:
                logger.info(f"  reference_base_prompt:")
                logger.info(f"    Before: {original[:80]}...")
                logger.info(f"    After:  {normalized[:80]}...")
                char.reference_base_prompt = normalized
                changed = True
            else:
                logger.info(f"  reference_base_prompt: OK (no changes)")

        if changed:
            updated_count += 1

    logger.info(f"\n{'='*60}")
    if dry_run:
        logger.info(f"🔍 DRY RUN - No changes committed")
        logger.info(f"Characters that would be updated: {updated_count}/{len(characters)}")
        db.rollback()
    else:
        db.commit()
        logger.info(f"💾 Committed {updated_count} character updates")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Normalize character prompts to Danbooru standard"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to database (default is dry-run)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.debug:
        logger.setLevel("DEBUG")

    db = SessionLocal()
    try:
        normalize_all_characters(db, dry_run=not args.apply)
    finally:
        db.close()


if __name__ == "__main__":
    main()
