from config import logger
from database import SessionLocal
from models import Tag


def fix_misclassified_tags_2():
    db = SessionLocal()
    try:
        # 1. Update 'doremi' -> identity (character trigger)
        doremi = db.query(Tag).filter(Tag.name == "doremi").first()
        if doremi:
            logger.info(f"Updating 'doremi': {doremi.group_name} -> identity")
            doremi.group_name = "identity"
            doremi.category = "identity"  # Since it's a character trigger

        # 2. Update 'casual_outfit' -> clothing
        casual = db.query(Tag).filter(Tag.name == "casual_outfit").first()
        if casual:
            logger.info(f"Updating 'casual_outfit': {casual.group_name} -> clothing")
            casual.group_name = "clothing"
            casual.category = "character"  # usually clothing is character related

        db.commit()
        logger.info("✅ Tag classification fixes (Batch 2) applied.")

    except Exception as e:
        logger.error(f"Failed to fix tags: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    fix_misclassified_tags_2()
