"""Fix default_layer for all tags with group_name using GROUP_NAME_TO_LAYER SSOT.

Usage:
    python scripts/fix_tag_default_layers.py --dry-run   # preview changes
    python scripts/fix_tag_default_layers.py              # apply changes
"""

import argparse

from config import logger
from database import SessionLocal
from models import Tag
from services.keywords.patterns import GROUP_NAME_TO_LAYER


def fix_tag_default_layers(dry_run: bool = False) -> None:
    db = SessionLocal()
    try:
        tags = db.query(Tag).filter(Tag.group_name.isnot(None)).all()
        fixed, skipped = 0, 0

        for tag in tags:
            expected = GROUP_NAME_TO_LAYER.get(tag.group_name) if tag.group_name else None
            if expected is None:
                skipped += 1
                continue
            if tag.default_layer == expected:
                skipped += 1
                continue

            logger.info(
                "[%s] %s: default_layer %d -> %d (group=%s)",
                "DRY-RUN" if dry_run else "FIX",
                tag.name,
                tag.default_layer,
                expected,
                tag.group_name,
            )
            if not dry_run:
                tag.default_layer = expected
            fixed += 1

        if not dry_run:
            db.commit()

        logger.info(
            "Done (%s): %d fixed, %d skipped (total %d)",
            "dry-run" if dry_run else "applied",
            fixed,
            skipped,
            len(tags),
        )
    except Exception as e:
        logger.error("Failed: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix tag default_layer values")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    args = parser.parse_args()
    fix_tag_default_layers(dry_run=args.dry_run)
